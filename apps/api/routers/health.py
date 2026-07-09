"""Sonde de vie + diagnostic — utilisées par Render et le monitoring."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.core.config import settings
from apps.api.db import engine, get_db
from apps.api.db_models import Customer, Payment, Search

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.version}


@router.get("/health/diag")
def diag(db: Session = Depends(get_db)) -> dict:
    """
    Diagnostic read-only (aucun secret, aucune donnée personnelle).

    - `db` : moteur réellement utilisé ("postgresql" attendu en prod, "sqlite"
      signale que DATABASE_URL n'est pas branché → base éphémère).
    - compteurs : si `payments` reste à 0 après un paiement, le webhook n'a jamais
      crédité (signature/livraison Stripe).
    """
    return {
        "db": engine.dialect.name,
        "customers": db.query(Customer).count(),
        "payments": db.query(Payment).count(),
        "searches": db.query(Search).count(),
    }
