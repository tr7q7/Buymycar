"""
Filet de sécurité — modèles DB (crédits / paiements / recherches).

Teste les modèles ORM sur une base SQLite en mémoire isolée (n'utilise pas
l'engine global), pour valider schéma et valeurs par défaut.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.db import Base
import apps.api.db_models  # noqa: F401 — enregistre les tables sur Base
from apps.api.db_models import Customer, Payment, Search


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def test_tables_creees():
    assert {"customers", "payments", "searches"} <= set(Base.metadata.tables)


def test_customer_defauts(session):
    c = Customer(email="a@b.com", credits_remaining=2)
    session.add(c)
    session.commit()

    got = session.get(Customer, "a@b.com")
    assert got is not None
    assert got.credits_remaining == 2
    assert isinstance(got.created_at, datetime)
    assert isinstance(got.updated_at, datetime)


def test_payment_pk_session(session):
    p = Payment(
        stripe_session_id="cs_test_123",
        email="a@b.com",
        amount=200,
        credits_added=10,
        status="paid",
    )
    session.add(p)
    session.commit()

    got = session.get(Payment, "cs_test_123")
    assert got.email == "a@b.com"
    assert got.amount == 200
    assert got.credits_added == 10


def test_search_autoincrement(session):
    session.add(Search(email="a@b.com", search_id="job-1"))
    session.add(Search(email="a@b.com", search_id="job-2"))
    session.commit()

    rows = session.query(Search).order_by(Search.id).all()
    assert [r.search_id for r in rows] == ["job-1", "job-2"]
    assert rows[0].id != rows[1].id
