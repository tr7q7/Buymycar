"""
Service Stripe — Checkout (prix dynamique) et traitement du webhook.

- Création de session : mode "payment" (jamais d'abonnement), prix dynamique
  price_data (montant/devise depuis la config), pack de 5 crédits.
- Webhook : vérification de signature + crédit idempotent (table payments, PK =
  stripe_session_id → un webhook répété ne crédite jamais deux fois).

Aucune clé en dur : tout vient de core.config.settings (env).
Apple Pay / Google Pay s'affichent automatiquement dans Stripe Checkout pour les
utilisateurs éligibles (aucune config de payment_method_types nécessaire).
"""

import logging
from typing import Optional

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.core.config import settings
from apps.api.db_models import Customer, Payment
from apps.api import credits_service

logger = logging.getLogger("autocote.stripe")

# Un pack = 5 analyses.
CREDITS_PER_PACK = 5
PRODUCT_NAME = "Pack 5 analyses AutoCote"


class StripeNotConfigured(Exception):
    """La clé secrète Stripe n'est pas configurée côté serveur."""


class WebhookVerificationError(Exception):
    """Signature de webhook invalide ou corps illisible."""


def _sget(obj, key, default=None):
    """
    Lecture sûre d'une clé, compatible StripeObject ET dict.

    Les objets Stripe (StripeObject) ne supportent PAS `.get()` : `obj.get`
    est résolu comme un champ nommé « get » et lève une erreur. On utilise donc
    l'indexation `obj[key]`, gérée par StripeObject comme par dict.
    """
    try:
        value = obj[key]
    except (KeyError, TypeError):
        return default
    return default if value is None else value


def create_checkout_session(email: str) -> str:
    """Crée une session Stripe Checkout et renvoie son URL de paiement."""
    if not settings.stripe_secret_key:
        raise StripeNotConfigured("STRIPE_SECRET_KEY absente.")

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=email,
        line_items=[
            {
                "price_data": {
                    "currency": settings.stripe_currency,
                    "unit_amount": settings.stripe_price_amount,
                    "product_data": {"name": PRODUCT_NAME},
                },
                "quantity": 1,
            }
        ],
        metadata={"email": email, "credits": str(CREDITS_PER_PACK)},
        success_url=f"{settings.frontend_url}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/?payment=cancel",
    )
    return session.url


def handle_webhook_event(db: Session, payload: bytes, sig_header: str) -> dict:
    """
    Vérifie la signature puis traite l'événement.

    Sur checkout.session.completed : crédite +10 de façon idempotente.
    L'unicité de payments.stripe_session_id garantit qu'un webhook rejoué
    ne crédite pas une seconde fois.
    """
    # STRIPE_WEBHOOK_SECRET peut contenir plusieurs secrets séparés par des virgules
    # (ex. "whsec_test,whsec_live") : on essaie chacun jusqu'à ce que la signature
    # soit valide → test ET live fonctionnent simultanément.
    raw = settings.stripe_webhook_secret or ""
    secrets = [s.strip() for s in raw.split(",") if s.strip()] or [raw]
    event = None
    last_err: Exception | None = None
    for secret in secrets:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
            break
        except Exception as e:  # signature invalide pour ce secret
            last_err = e
    if event is None:
        logger.warning(
            "[stripe.webhook] signature invalide (aucun des %d secret(s) ne correspond) : %s",
            len(secrets), last_err,
        )
        raise WebhookVerificationError(str(last_err) if last_err else "secret manquant")

    if event["type"] != "checkout.session.completed":
        logger.info("[stripe.webhook] événement ignoré type=%s", event["type"])
        return {"status": "ignored", "type": event["type"]}

    session = event["data"]["object"]
    session_id = _sget(session, "id")
    meta = _sget(session, "metadata") or {}
    customer_email = _sget(session, "customer_email")
    meta_email = _sget(meta, "email")
    email = meta_email or customer_email
    credits = int(_sget(meta, "credits", CREDITS_PER_PACK) or CREDITS_PER_PACK)
    amount = _sget(session, "amount_total") or 0

    logger.info(
        "[stripe.webhook] reçu session=%s customer_email=%s metadata_email=%s credits=%s",
        session_id, customer_email, meta_email, credits,
    )
    return _credit_session(db, session_id, email, credits, amount, source="webhook")


def _credit_session(
    db: Session,
    session_id: str,
    email: Optional[str],
    credits: int,
    amount: int,
    source: str,
) -> dict:
    """
    Crédite un email pour une session Stripe, de façon idempotente.

    Utilisé par le webhook ET par la confirmation au retour : l'unicité de
    payments.stripe_session_id garantit qu'un même paiement ne crédite qu'une fois,
    même si le webhook et la confirmation arrivent tous les deux.
    """
    if not email:
        logger.warning("[stripe.%s] email absent session=%s", source, session_id)
        return {"status": "skipped", "reason": "email absent"}

    email = credits_service.normalize_email(email)

    db.add(
        Payment(
            stripe_session_id=session_id,
            email=email,
            amount=amount,
            credits_added=credits,
            status="paid",
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # Déjà traité pour cette session → aucun crédit ajouté. On renvoie le solde.
        db.rollback()
        customer = db.get(Customer, email)
        balance = customer.credits_remaining if customer else None
        logger.info("[stripe.%s] déjà traité session=%s email=%s", source, session_id, email)
        return {"status": "already_processed", "email": email, "balance": balance}

    balance = credits_service.add_credits(db, email, credits)
    logger.info(
        "[stripe.%s] crédité email=%s +%s -> solde=%s (session=%s)",
        source, email, credits, balance, session_id,
    )
    return {
        "status": "credited",
        "email": email,
        "credits_added": credits,
        "balance": balance,
    }


def confirm_checkout_session(db: Session, session_id: str) -> dict:
    """
    Confirme un paiement au retour de Stripe, SANS dépendre du webhook.

    Récupère la session via l'API Stripe (clé secrète), vérifie qu'elle est payée,
    puis crédite (idempotent, même garde que le webhook). Rend le système robuste
    même si le webhook est mal configuré.
    """
    if not settings.stripe_secret_key:
        raise StripeNotConfigured("STRIPE_SECRET_KEY absente.")

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.retrieve(session_id)

    payment_status = _sget(session, "payment_status")
    if payment_status != "paid":
        logger.info(
            "[stripe.confirm] session=%s non payée (payment_status=%s)",
            session_id, payment_status,
        )
        return {"status": "unpaid", "payment_status": payment_status}

    meta = _sget(session, "metadata") or {}
    email = _sget(meta, "email") or _sget(session, "customer_email")
    credits = int(_sget(meta, "credits", CREDITS_PER_PACK) or CREDITS_PER_PACK)
    amount = _sget(session, "amount_total") or 0

    logger.info(
        "[stripe.confirm] session=%s payée email=%s credits=%s", session_id, email, credits
    )
    return _credit_session(db, session_id, email, credits, amount, source="confirm")
