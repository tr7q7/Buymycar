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

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
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


# ── Anti-abus visitor_id ──────────────────────────────────────────────────────

class TestVisitorAntiAbuse:
    def test_nouvel_email_nouvel_appareil_2_credits(self, db):
        c, blocked = credits_service.init_free_credits(db, "a@b.fr", "device-1")
        assert c.credits_remaining == 2
        assert blocked is False

    def test_nouvel_email_meme_appareil_pas_de_credits(self, db):
        credits_service.init_free_credits(db, "a@b.fr", "device-1")
        c2, blocked = credits_service.init_free_credits(db, "autre@b.fr", "device-1")
        assert c2.credits_remaining == 0
        assert blocked is True

    def test_email_existant_inchange(self, db):
        credits_service.init_free_credits(db, "a@b.fr", "device-1")
        credits_service.decrement(db, "a@b.fr")  # 2 -> 1
        c, blocked = credits_service.init_free_credits(db, "a@b.fr", "device-1")
        assert c.credits_remaining == 1  # pas remis à 2
        assert blocked is False

    def test_sans_visitor_id_comportement_historique(self, db):
        c, blocked = credits_service.init_free_credits(db, "a@b.fr", None)
        assert c.credits_remaining == 2
        assert blocked is False

    def test_appareils_differents_chacun_ses_credits(self, db):
        c1, _ = credits_service.init_free_credits(db, "a@b.fr", "device-1")
        c2, blocked = credits_service.init_free_credits(db, "b@b.fr", "device-2")
        assert c1.credits_remaining == 2
        assert c2.credits_remaining == 2
        assert blocked is False


# ── Endpoints ─────────────────────────────────────────────────────────────────

class TestCreditsRouter:
    def test_init_cree_2_credits(self, client):
        r = client.post("/credits/init", json={"email": "pro@garage.fr"})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "pro@garage.fr"
        assert body["credits_remaining"] == 2
        assert body["device_blocked"] is False

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

    def test_init_meme_appareil_bloque(self, client):
        client.post("/credits/init", json={"email": "a@b.fr", "visitor_id": "dev-x"})
        r = client.post(
            "/credits/init", json={"email": "autre@b.fr", "visitor_id": "dev-x"}
        )
        body = r.json()
        assert body["credits_remaining"] == 0
        assert body["device_blocked"] is True
