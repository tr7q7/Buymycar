"""
Filet de sécurité — Stripe (checkout + webhook) sans appel réseau.

stripe.Webhook.construct_event et stripe.checkout.Session.create sont mockés :
aucun appel réel à Stripe.
"""

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.api.db import Base, get_db
import apps.api.db_models  # noqa: F401
from apps.api.db_models import Payment
from apps.api.core.config import settings


@pytest.fixture
def env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    yield TestClient(app), Session
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


class _StripeLikeObject:
    """
    Reproduit le comportement d'un StripeObject réel : indexation `obj[key]` OK,
    mais `obj.get(...)` lève (comme en prod) — pour empêcher toute régression.
    """

    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key):
        value = self._data[key]
        return _StripeLikeObject(value) if isinstance(value, dict) else value

    def __contains__(self, key):
        return key in self._data

    def __getattr__(self, name):
        # Comme StripeObject : un attribut absent (ex. .get) devient une recherche
        # de champ, qui lève AttributeError si absent.
        try:
            return self.__dict__["_data"][name]
        except KeyError as e:
            raise AttributeError(name) from e


def _completed_event(session_id: str = "cs_1", email: str = "buy@test.fr"):
    # Enveloppé en objet « façon Stripe » (sans .get) pour coller à la réalité.
    return _StripeLikeObject(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "metadata": {"email": email, "credits": "10"},
                    "amount_total": 200,
                    "customer_email": email,
                }
            },
        }
    )


def _post_webhook(client: TestClient):
    return client.post(
        "/stripe/webhook", content=b"{}", headers={"stripe-signature": "t"}
    )


# ── Webhook ───────────────────────────────────────────────────────────────────

def test_webhook_credite_10(env, monkeypatch):
    client, Session = env
    monkeypatch.setattr(stripe.Webhook, "construct_event",
                        lambda *a, **k: _completed_event())

    r = _post_webhook(client)
    assert r.status_code == 200
    assert r.json()["status"] == "credited"

    # +10 crédits pour l'email
    bal = client.get("/credits", params={"email": "buy@test.fr"}).json()
    assert bal["credits_remaining"] == 10

    # paiement enregistré
    s = Session()
    assert s.get(Payment, "cs_1") is not None
    s.close()


def test_webhook_repete_ne_credite_pas_deux_fois(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(stripe.Webhook, "construct_event",
                        lambda *a, **k: _completed_event())

    _post_webhook(client)
    r2 = _post_webhook(client)
    assert r2.json()["status"] == "already_processed"

    bal = client.get("/credits", params={"email": "buy@test.fr"}).json()
    assert bal["credits_remaining"] == 10  # crédité une seule fois


def test_webhook_type_ignore(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(
        stripe.Webhook, "construct_event",
        lambda *a, **k: {"type": "payment_intent.created", "data": {"object": {}}},
    )
    r = _post_webhook(client)
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_webhook_signature_invalide_400(env, monkeypatch):
    client, _ = env

    def boom(*a, **k):
        raise ValueError("bad signature")
    monkeypatch.setattr(stripe.Webhook, "construct_event", boom)

    r = client.post("/stripe/webhook", content=b"{}",
                    headers={"stripe-signature": "bad"})
    assert r.status_code == 400


# ── Création de session ───────────────────────────────────────────────────────

def test_checkout_non_configure_503(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    r = client.post("/checkout/create-session", json={"email": "a@b.fr"})
    assert r.status_code == 503


def test_checkout_cree_session_et_renvoie_url(env, monkeypatch):
    client, _ = env
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")

    class FakeSession:
        url = "https://checkout.stripe.com/pay/cs_test_123"

    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **k: FakeSession())

    r = client.post("/checkout/create-session", json={"email": "a@b.fr"})
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://checkout.stripe.com/")
