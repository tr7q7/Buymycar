"""
Service Stripe — Checkout (prix dynamique) et traitement du webhook.

- Création de session : mode "payment" (jamais d'abonnement), prix dynamique
  price_data (montant/devise depuis la config), pack de 10 crédits.
- Webhook : vérification de signature + crédit idempotent (table payments, PK =
  stripe_session_id → un webhook répété ne crédite jamais deux fois).

Aucune clé en dur : tout vient de core.config.settings (env).
Apple Pay / Google Pay s'affichent automatiquement dans Stripe Checkout pour les
utilisateurs éligibles (aucune config de payment_method_types nécessaire).
"""

import logging

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.core.config import settings
from apps.api.db_models import Payment
from apps.api import credits_service

logger = logging.getLogger("autocote.stripe")

# Un pack = 10 analyses.
CREDITS_PER_PACK = 10
PRODUCT_NAME = "Pack 10 analyses AutoCote"


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
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except Exception as e:  # signature invalide, corps illisible…
        raise WebhookVerificationError(str(e)) from e

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored", "type": event["type"]}

    session = event["data"]["object"]
    session_id = _sget(session, "id")
    meta = _sget(session, "metadata") or {}
    customer_email = _sget(session, "customer_email")
    meta_email = _sget(meta, "email")
    email = meta_email or customer_email
    credits = int(_sget(meta, "credits", CREDITS_PER_PACK) or CREDITS_PER_PACK)
    amount = _sget(session, "amount_total") or 0

    # Diagnostic (sans secret) — visible dans les logs Render.
    logger.info(
        "[stripe.webhook] reçu session=%s customer_email=%s metadata_email=%s credits=%s",
        session_id, customer_email, meta_email, credits,
    )

    if not email:
        logger.warning("[stripe.webhook] email absent session=%s", session_id)
        return {"status": "skipped", "reason": "email absent"}

    email = credits_service.normalize_email(email)

    # Garde d'idempotence : on insère d'abord le paiement (PK = session_id).
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
        # Webhook déjà traité pour cette session → aucun crédit ajouté.
        db.rollback()
        logger.info("[stripe.webhook] déjà traité session=%s email=%s", session_id, email)
        return {"status": "already_processed", "session_id": session_id}

    balance = credits_service.add_credits(db, email, credits)
    logger.info(
        "[stripe.webhook] crédité email=%s +%s -> solde=%s (session=%s)",
        email, credits, balance, session_id,
    )
    return {
        "status": "credited",
        "email": email,
        "credits_added": credits,
        "balance": balance,
    }
