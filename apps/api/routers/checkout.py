"""
Checkout — création d'une session Stripe pour acheter un pack de 5 analyses.

POST /checkout/create-session : {email} → {url} (URL de paiement Stripe Checkout).
Le front redirige l'utilisateur vers cette URL.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from apps.api.credits_service import validate_email
from apps.api.db import get_db
from apps.api import stripe_service

router = APIRouter(prefix="/checkout", tags=["checkout"])


class CheckoutRequest(BaseModel):
    email: str
    visitor_id: str = ""

    @field_validator("email")
    @classmethod
    def _check(cls, v: str) -> str:
        return validate_email(v)


class CheckoutOut(BaseModel):
    url: str


class ConfirmRequest(BaseModel):
    session_id: str


@router.post("/create-session", response_model=CheckoutOut)
def create_session(req: CheckoutRequest) -> CheckoutOut:
    try:
        url = stripe_service.create_checkout_session(req.email, req.visitor_id)
    except stripe_service.StripeNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Paiement momentanément indisponible.",
        )
    return CheckoutOut(url=url)


@router.post("/confirm")
def confirm(req: ConfirmRequest, db: Session = Depends(get_db)) -> dict:
    """
    Confirme un paiement au retour de Stripe (indépendant du webhook).

    Le front appelle cet endpoint avec le session_id présent dans l'URL de retour ;
    on récupère la session côté Stripe et on crédite si elle est payée. Idempotent.
    """
    try:
        return stripe_service.confirm_checkout_session(db, req.session_id)
    except stripe_service.StripeNotConfigured:
        raise HTTPException(status_code=503, detail="Paiement momentanément indisponible.")
    except Exception as e:  # session inconnue / erreur Stripe
        raise HTTPException(status_code=400, detail=f"Session invalide : {e}")
