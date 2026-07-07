"""
Webhook Stripe — source de vérité du crédit après paiement.

POST /stripe/webhook : vérifie la signature Stripe puis, sur
checkout.session.completed, crédite +10 de façon idempotente.

La vérification de signature se fait sur le CORPS BRUT de la requête (indispensable :
tout reformatage invaliderait la signature).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api import stripe_service

router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()  # corps brut, requis pour la signature
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = stripe_service.handle_webhook_event(db, payload, sig_header)
    except stripe_service.WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Signature invalide")

    return {"received": True, **result}
