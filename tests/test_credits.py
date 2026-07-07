"""
Filet de sécurité — service crédits et routeur /credits.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.db import Base, get_db
import apps.api.db_models  # noqa: F401
from apps.api import credits_service
from apps.api.credits_service import FREE_CREDITS
from apps.api.main import app


def _memory_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db():
    engine = _memory_engine()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client():
    engine = _memory_engine()
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


# ── Service ───────────────────────────────────────────────────────────────────

class TestCreditsService:
    def test_email_inconnu_recoit_2_credits(self, db):
        c = credits_service.get_or_create(db, "pro@garage.fr")
        assert c.credits_remaining == FREE_CREDITS == 2

    def test_email_connu_non_recree(self, db):
        credits_service.get_or_create(db, "pro@garage.fr")
        credits_service.decrement(db, "pro@garage.fr")  # 2 -> 1
        again = credits_service.get_or_create(db, "pro@garage.fr")
        assert again.credits_remaining == 1  # PAS remis à 2

    def test_get_credits_inconnu_zero(self, db):
        assert credits_service.get_credits(db, "nobody@x.fr") == 0

    def test_decrement_consomme_un_credit(self, db):
        credits_service.get_or_create(db, "a@b.fr")
        assert credits_service.decrement(db, "a@b.fr") is True
        assert credits_service.get_credits(db, "a@b.fr") == 1

    def test_decrement_a_zero_refuse(self, db):
        credits_service.get_or_create(db, "a@b.fr")
        credits_service.decrement(db, "a@b.fr")  # 2->1
        credits_service.decrement(db, "a@b.fr")  # 1->0
        assert credits_service.decrement(db, "a@b.fr") is False  # 0 -> refus
        assert credits_service.get_credits(db, "a@b.fr") == 0

    def test_add_credits(self, db):
        credits_service.get_or_create(db, "a@b.fr")
        new_balance = credits_service.add_credits(db, "a@b.fr", 10)
        assert new_balance == 12

    def test_email_normalise(self, db):
        credits_service.get_or_create(db, "  Pro@Garage.FR ")
        assert credits_service.get_credits(db, "pro@garage.fr") == 2


# ── Endpoints ─────────────────────────────────────────────────────────────────

class TestCreditsRouter:
    def test_init_cree_2_credits(self, client):
        r = client.post("/credits/init", json={"email": "pro@garage.fr"})
        assert r.status_code == 200
        assert r.json() == {"email": "pro@garage.fr", "credits_remaining": 2}

    def test_init_repete_ne_double_pas(self, client):
        client.post("/credits/init", json={"email": "pro@garage.fr"})
        r = client.post("/credits/init", json={"email": "pro@garage.fr"})
        assert r.json()["credits_remaining"] == 2  # toujours 2, pas 4

    def test_get_credits(self, client):
        client.post("/credits/init", json={"email": "pro@garage.fr"})
        r = client.get("/credits", params={"email": "pro@garage.fr"})
        assert r.status_code == 200
        assert r.json()["credits_remaining"] == 2

    def test_email_invalide_rejete(self, client):
        r = client.post("/credits/init", json={"email": "pasunemail"})
        assert r.status_code == 422
