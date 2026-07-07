"""
Service crédits — logique métier des crédits par email.

Identité = email (pas de compte, pas de login). Volontairement simple et testable :
les fonctions prennent une Session SQLAlchemy et ne connaissent pas HTTP.

Règle produit : 2 recherches gratuites par email, puis packs de 10 achetés.
"""

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db_models import Customer

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
