"""
Crédits — initialisation et consultation par email.

POST /credits/init  : crée l'email avec 2 crédits gratuits s'il est inconnu.
GET  /credits       : consulte le solde d'un email.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api import credits_service
from apps.api.credits_service import validate_email

router = APIRouter(prefix="/credits", tags=["credits"])


class CreditsInitRequest(BaseModel):
    email: str
    visitor_id: str = ""

    @field_validator("email")
    @classmethod
    def _check(cls, v: str) -> str:
        return validate_email(v)


class CreditsOut(BaseModel):
    email: str
    credits_remaining: int
    device_blocked: bool = False


@router.post("/init", response_model=CreditsOut)
def init_credits(req: CreditsInitRequest, db: Session = Depends(get_db)) -> CreditsOut:
    customer, device_blocked = credits_service.init_free_credits(
        db, req.email, req.visitor_id
    )
    return CreditsOut(
        email=customer.email,
        credits_remaining=customer.credits_remaining,
        device_blocked=device_blocked,
    )


@router.get("", response_model=CreditsOut)
def read_credits(
    email: str = Query(..., examples=["pro@garage.fr"]),
    db: Session = Depends(get_db),
) -> CreditsOut:
    try:
        email = validate_email(email)
    except ValueError:
        raise HTTPException(status_code=422, detail="Email invalide")
    return CreditsOut(
        email=credits_service.normalize_email(email),
        credits_remaining=credits_service.get_credits(db, email),
    )
