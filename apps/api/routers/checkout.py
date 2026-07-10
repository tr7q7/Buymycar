"""
Checkout — création d'une session Stripe pour acheter un pack de 5 analyses.

POST /checkout/create-session : {email} → {url} (URL de paiement Stripe Checkout).
Le front redirige l'utilisateur vers cette URL.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from apps.api.credits_service import validate_email
from apps.api import stripe_service

router = APIRouter(prefix="/checkout", tags=["checkout"])


class CheckoutRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _check(cls, v: str) -> str:
        return validate_email(v)


class CheckoutOut(BaseModel):
    url: str


@router.post("/create-session", response_model=CheckoutOut)
def create_session(req: CheckoutRequest) -> CheckoutOut:
    try:
        url = stripe_service.create_checkout_session(req.email)
    except stripe_service.StripeNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Paiement momentanément indisponible.",
        )
    return CheckoutOut(url=url)
