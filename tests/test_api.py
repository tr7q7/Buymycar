"""
Filet de sécurité — couche API FastAPI.

Teste le câblage HTTP (health, catalog, search async+polling, contrôle des crédits)
sans appel réseau : run_search est mocké pour renvoyer un SearchResult instantané.
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
import apps.api.routers.search as search_router
from apps.api.db import Base, get_db
import apps.api.db_models  # noqa: F401
from apps.api import credits_service
from app.services.search_service import SearchResult
from app.services.filtering_service import FilterResult
from app.providers.piloterr_provider import PiloterrMeta
from app.analytics.market_price_estimator import MarketEstimate

client = TestClient(app)


@pytest.fixture
def db_env():
    """Base de test isolée (in-memory) + provisionnement de crédits.

    Installe un override de get_db le temps du test et le retire proprement
    (sans écraser un éventuel override posé par un autre module de test).
    """
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

    def seed(email: str, credits: int = 2) -> None:
        s = Session()
        try:
            credits_service.add_credits(s, email, credits)
        finally:
            s.close()

    yield seed

    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


# ── Health & catalogue ────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_catalog_brands_contient_audi():
    r = client.get("/catalog/brands")
    assert r.status_code == 200
    brands = r.json()
    assert "Audi" in brands
    assert brands == sorted(brands)


def test_catalog_models_audi_contient_rs3():
    r = client.get("/catalog/models", params={"brand": "Audi"})
    assert r.status_code == 200
    assert "RS3" in r.json()


def test_catalog_fuels_rs3_essence_seule():
    r = client.get("/catalog/fuels", params={"brand": "Audi", "model": "RS3"})
    assert r.status_code == 200
    assert r.json() == ["essence"]


# ── Recherche async ───────────────────────────────────────────────────────────

def _poll_until_done(job_id: str, timeout_s: float = 3.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get(f"/search/{job_id}")
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.02)
    raise AssertionError("Le job n'a pas abouti dans le délai imparti")


def _fake_result(make) -> SearchResult:
    listing = make(id="1", brand="Audi", model="rs3",
                   title="Audi RS3", fuel="essence", year=2020, price=45000)
    # Modèle générique « Autres » + titre à espaces multiples : doit être nettoyé.
    listing_generic = make(id="2", brand="Audi", model="Autres",
                           title="Audi  RS3   Berline", fuel="essence",
                           year=2021, price=52000)
    return SearchResult(
        listings=[listing, listing_generic],
        stats={"count": 2, "mean": 48500, "median": 48500,
               "min": 45000, "max": 52000, "stdev": 4950},
        low_price_excluded=0,
        filt=FilterResult(listings=[listing, listing_generic], strict_count=2, level=1,
                          year_min_used=2018, year_max_used=2026),
        meta=PiloterrMeta(total_results=2, returned_results=2),
        lbc_url="https://www.leboncoin.fr/recherche?text=audi+rs3",
        raw_count=2,
        strategy="standard",
        market_est=MarketEstimate(
            estimated=48000, low=45000, high=52000, n_used=2,
            effective_n=2.0, confidence="Faible", cv=0.1,
        ),
    )


def _payload(email: str) -> dict:
    return {
        "email": email, "brand": "audi", "model": "rs3", "fuel": "essence",
        "year_min": 2018, "year_max": 2026,
    }


def test_search_job_cycle_complet(make, monkeypatch, db_env):
    db_env("cycle@test.fr", credits=2)
    monkeypatch.setattr(search_router, "run_search", lambda *a, **k: _fake_result(make))

    r = client.post("/search", json=_payload("cycle@test.fr"))
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    body = _poll_until_done(job_id)
    result = body["result"]
    assert body["status"] == "done"
    assert result["strategy"] == "standard"
    assert result["listings"][0]["model"] == "rs3"
    assert result["filter"]["retained"] == 2

    # Nettoyage d'affichage : modèle générique masqué, titre compacté
    assert result["listings"][1]["model"] == ""
    assert result["listings"][1]["title"] == "Audi RS3 Berline"

    # Valeur marché estimée exposée
    assert result["market_estimate"]["estimated"] == 48000
    assert result["market_estimate"]["confidence"] == "Faible"


def test_search_job_erreur_remontee(monkeypatch, db_env):
    db_env("err@test.fr", credits=2)

    def boom(*a, **k):
        raise RuntimeError("Piloterr indisponible")
    monkeypatch.setattr(search_router, "run_search", boom)

    r = client.post("/search", json=_payload("err@test.fr"))
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    body = _poll_until_done(job_id)
    assert body["status"] == "error"
    assert "Piloterr indisponible" in body["error"]


def test_search_job_inexistant_404():
    r = client.get("/search/inexistant")
    assert r.status_code == 404


# ── Contrôle des crédits sur /search ──────────────────────────────────────────

def test_search_decremente_un_credit(make, monkeypatch, db_env):
    db_env("dec@test.fr", credits=2)
    monkeypatch.setattr(search_router, "run_search", lambda *a, **k: _fake_result(make))

    r = client.post("/search", json=_payload("dec@test.fr"))
    assert r.status_code == 202

    # 2 -> 1 après une recherche acceptée
    c = client.get("/credits", params={"email": "dec@test.fr"})
    assert c.json()["credits_remaining"] == 1


def test_search_sans_credit_renvoie_402(db_env):
    # Email sans crédit (jamais provisionné) → refus, aucun job lancé.
    r = client.post("/search", json=_payload("broke@test.fr"))
    assert r.status_code == 402
    assert r.json()["detail"] == "NEED_CREDITS"


def test_search_email_manquant_422(db_env):
    payload = _payload("x@y.fr")
    del payload["email"]
    r = client.post("/search", json=payload)
    assert r.status_code == 422
