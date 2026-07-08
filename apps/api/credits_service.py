"""
Service crédits — logique métier des crédits par email.

Identité = email (pas de compte, pas de login). Volontairement simple et testable :
les fonctions prennent une Session SQLAlchemy et ne connaissent pas HTTP.

Règle produit : 2 recherches gratuites par email, puis packs de 10 achetés.
"""

from typing import Optional, Tuple

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db_models import Customer, Visitor

# Crédits offerts à la création d'un email inconnu.
FREE_CREDITS = 2


def normalize_email(email: str) -> str:
    """Normalise un email (trim + minuscules) pour une identité stable."""
    return email.strip().lower()


def validate_email(value: str) -> str:
    """Validation minimale (MVP) : présence d'un @ et d'un domaine avec point."""
    v = (value or "").strip()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
        raise ValueError("Email invalide")
    return v


def get_or_create(db: Session, email: str) -> Customer:
    """Retourne le client, en le créant avec FREE_CREDITS s'il est inconnu."""
    email = normalize_email(email)
    customer = db.get(Customer, email)
    if customer is not None:
        return customer

    customer = Customer(email=email, credits_remaining=FREE_CREDITS)
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        # Course : un autre appel concurrent a créé le même email entre-temps.
        db.rollback()
        customer = db.get(Customer, email)
    return customer


def init_free_credits(
    db: Session,
    email: str,
    visitor_id: Optional[str] = None,
) -> Tuple[Customer, bool]:
    """
    Initialise un email en tenant compte de l'anti-abus par appareil.

    Règle :
      - 2 crédits gratuits maximum par email ;
      - 2 crédits gratuits maximum par visitor_id (appareil).
    Un email existant n'est jamais modifié. Un email NOUVEAU depuis un appareil
    ayant déjà consommé ses crédits gratuits est créé avec 0 crédit.

    Renvoie (customer, device_blocked) où device_blocked=True indique que les
    crédits gratuits ont été refusés à cause de l'appareil.
    """
    email = normalize_email(email)
    customer = db.get(Customer, email)
    if customer is not None:
        return customer, False  # compte existant : aucun changement

    grant = FREE_CREDITS
    device_blocked = False
    vid = (visitor_id or "").strip()
    if vid:
        visitor = db.get(Visitor, vid)
        if visitor is not None and visitor.free_granted:
            grant = 0
            device_blocked = True
        elif visitor is None:
            db.add(Visitor(visitor_id=vid, free_granted=True))
        else:
            visitor.free_granted = True

    customer = Customer(email=email, credits_remaining=grant)
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        # Course : email créé entre-temps → on renvoie l'existant, sans blocage.
        db.rollback()
        return db.get(Customer, email), False
    return customer, device_blocked


def get_credits(db: Session, email: str) -> int:
    """Crédits restants pour un email (0 si inconnu, sans le créer)."""
    customer = db.get(Customer, normalize_email(email))
    return customer.credits_remaining if customer else 0


def decrement(db: Session, email: str) -> bool:
    """
    Décrémente 1 crédit de façon atomique.

    Renvoie True si un crédit a bien été consommé, False si solde nul / inconnu.
    L'UPDATE conditionnel (credits_remaining > 0) empêche tout double décrément
    ou passage en négatif, même sous concurrence.
    """
    email = normalize_email(email)
    result = db.execute(
        update(Customer)
        .where(Customer.email == email, Customer.credits_remaining > 0)
        .values(credits_remaining=Customer.credits_remaining - 1)
    )
    db.commit()
    return result.rowcount == 1


def add_credits(db: Session, email: str, amount: int) -> int:
    """Ajoute `amount` crédits (crée le client si besoin). Renvoie le nouveau solde."""
    email = normalize_email(email)
    customer = db.get(Customer, email)
    if customer is None:
        customer = Customer(email=email, credits_remaining=amount)
        db.add(customer)
    else:
        customer.credits_remaining += amount
    db.commit()
    return customer.credits_remaining
