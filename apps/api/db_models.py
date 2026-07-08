"""
Modèles ORM — crédits, paiements, recherches.

Modèle MVP volontairement simple : identité = email (pas de compte, pas de login).
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Payment(Base):
    __tablename__ = "payments"

    stripe_session_id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)          # centimes
    credits_added: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)
    search_id: Mapped[str] = mapped_column(String, nullable=False)        # = job_id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Visitor(Base):
    """
    Empreinte navigateur/appareil pour l'anti-abus des crédits gratuits.

    free_granted=True signifie que cet appareil a déjà bénéficié de ses crédits
    gratuits ; un nouvel email depuis le même appareil n'en reçoit alors plus.
    """
    __tablename__ = "visitors"

    visitor_id: Mapped[str] = mapped_column(String, primary_key=True)
    free_granted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
