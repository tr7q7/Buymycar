"""
Filet de sécurité — couche API FastAPI.

Teste le câblage HTTP (health, catalog, search async+polling) sans appel réseau :
run_search est mocké pour renvoyer un SearchResult instantané.
"""

import time

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
import apps.api.routers.search as search_router
from app.services.search_service import SearchResult
from app.services.filtering_service import FilterResult
from app.providers.piloterr_provider import PiloterrMeta

client = TestClient(app)


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


def test_search_job_cycle_complet(make, monkeypatch):
    listing = make(id="1", brand="Audi", model="rs3",
                   title="Audi RS3", fuel="essence", year=2020, price=45000)
    fake_result = SearchResult(
        listings=[listing],
        stats={"count": 1, "mean": 45000, "median": 45000,
               "min": 45000, "max": 45000, "stdev": 0},
        low_price_excluded=0,
        filt=FilterResult(listings=[listing], strict_count=1, level=1,
                          year_min_used=2018, year_max_used=2026),
        meta=PiloterrMeta(total_results=1, returned_results=1),
        lbc_url="https://www.leboncoin.fr/recherche?text=audi+rs3",
        raw_count=1,
        strategy="standard",
    )
    monkeypatch.setattr(search_router, "run_search", lambda *a, **k: fake_result)

    # POST → 202 + job_id
    r = client.post("/search", json={
        "brand": "audi", "model": "rs3", "fuel": "essence",
        "year_min": 2018, "year_max": 2026,
    })
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Polling → done + résultat sérialisé
    body = _poll_until_done(job_id)
    assert body["status"] == "done"
    assert body["result"]["strategy"] == "standard"
    assert body["result"]["listings"][0]["model"] == "rs3"
    assert body["result"]["filter"]["retained"] == 1


def test_search_job_erreur_remontee(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("Piloterr indisponible")
    monkeypatch.setattr(search_router, "run_search", boom)

    r = client.post("/search", json={
        "brand": "audi", "model": "rs3", "fuel": "essence",
        "year_min": 2018, "year_max": 2026,
    })
    job_id = r.json()["job_id"]
    body = _poll_until_done(job_id)
    assert body["status"] == "error"
    assert "Piloterr indisponible" in body["error"]


def test_search_job_inexistant_404():
    r = client.get("/search/inexistant")
    assert r.status_code == 404
