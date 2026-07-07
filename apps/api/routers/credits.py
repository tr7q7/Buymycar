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

router = APIRouter(prefix="/credits", tags=["credits"])


def _validate_email(value: str) -> str:
    v = (value or "").strip()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
        raise ValueError("Email invalide")
    return v


class CreditsInitRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _check(cls, v: str) -> str:
        return _validate_email(v)


class CreditsOut(BaseModel):
    email: str
    credits_remaining: int


@router.post("/init", response_model=CreditsOut)
def init_credits(req: CreditsInitRequest, db: Session = Depends(get_db)) -> CreditsOut:
    customer = credits_service.get_or_create(db, req.email)
    return CreditsOut(email=customer.email, credits_remaining=customer.credits_remaining)


@router.get("", response_model=CreditsOut)
def read_credits(
    email: str = Query(..., examples=["pro@garage.fr"]),
    db: Session = Depends(get_db),
) -> CreditsOut:
    try:
        email = _validate_email(email)
    except ValueError:
        raise HTTPException(status_code=422, detail="Email invalide")
    return CreditsOut(
        email=credits_service.normalize_email(email),
        credits_remaining=credits_service.get_credits(db, email),
    )
