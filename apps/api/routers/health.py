"""Sonde de vie + diagnostic — utilisées par Render et le monitoring."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.api.core.config import settings
from apps.api.db import engine, get_db
from apps.api.db_models import Customer, Payment, Search
from apps.api import credits_service

router = APIRouter(tags=["health"])


def _mask_email(email: str) -> str:
    """Masque un email : garde 3 lettres + domaine (ex. tho***@gmail.com)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:3]}***@{domain}"


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.version}


@router.get("/health/diag")
def diag(
    email: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """
    Diagnostic read-only (aucun secret ; emails masqués).

    - `db` : moteur réellement utilisé ("postgresql" attendu en prod).
    - `recent_payments` : derniers crédits webhook (email masqué + date) → permet
      de voir SUR QUEL email et QUAND les paiements ont crédité.
    - `?email=` : état d'un compte précis (solde, existence).
    """
    recent = (
        db.query(Payment).order_by(Payment.created_at.desc()).limit(5).all()
    )

    def _balance(mail: str):
        c = db.get(Customer, mail)
        return c.credits_remaining if c else None

    out = {
        "db": engine.dialect.name,
        "customers": db.query(Customer).count(),
        "payments": db.query(Payment).count(),
        "searches": db.query(Search).count(),
        "recent_payments": [
            {
                "email": _mask_email(p.email),
                "credits_added": p.credits_added,
                "current_balance": _balance(p.email),
                "amount": p.amount,
                "status": p.status,
                "created_at": str(p.created_at),
            }
            for p in recent
        ],
    }
    if email:
        c = db.get(Customer, credits_service.normalize_email(email))
        out["customer"] = {
            "email": _mask_email(email),
            "exists": c is not None,
            "credits_remaining": c.credits_remaining if c else None,
        }
    return out
