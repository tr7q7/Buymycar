"""
Filet de sécurité — orchestration de recherche (stratégie duale).

Cette logique était auparavant piégée dans main.py (_fetch_piloterr) et non testée.
On la teste ici via un faux provider (aucun appel réseau), en distinguant l'appel
brand+model de l'appel brand-only par le contenu de l'URL LeBonCoin.
"""

import pytest

from app.providers.piloterr_provider import PiloterrMeta
import app.services.search_service as search_service
from app.services.search_service import run_search


def _fake_provider_factory(url_to_listings):
    """Crée une classe FakeProvider qui renvoie des annonces selon l'URL reçue."""
    class FakeProvider:
        def __init__(self, search_params=None, lbc_url="", **kwargs):
            self.lbc_url = lbc_url

        def fetch_with_meta(self):
            # "text=audi+rs3" → appel brand+model ; "text=audi" seul → brand-only
            is_brand_only = "rs3" not in self.lbc_url.lower()
            listings = url_to_listings("brand_only" if is_brand_only else "brand_model")
            return listings, PiloterrMeta(returned_results=len(listings))

    return FakeProvider


class TestRunSearch:
    def test_strategie_standard_sans_second_appel(self, make, monkeypatch):
        # 25 RS3 exactes dès le 1er appel → strict_count >= 20 → pas d'élargissement
        def url_to_listings(kind):
            if kind == "brand_model":
                return [
                    make(id=str(i), brand="Audi", model="rs3",
                         title="Audi RS3", fuel="essence", year=2020, price=45000)
                    for i in range(25)
                ]
            raise AssertionError("Le 2e appel (brand-only) ne doit PAS avoir lieu")

        monkeypatch.setattr(search_service, "PiloterrProvider",
                            _fake_provider_factory(url_to_listings))

        res = run_search("audi", "rs3", "essence", 2018, 2026)
        assert res.strategy == "standard"
        assert res.filt.strict_count == 25
        assert len(res.listings) == 25

    def test_strategie_elargie_declenche_second_appel(self, make, monkeypatch):
        # 1er appel : 3 RS3 seulement → strict_count < 20 → déclenche brand-only
        # 2e appel : 25 RS3 supplémentaires (titre) → merge plus riche → "elargie"
        def url_to_listings(kind):
            if kind == "brand_model":
                return [
                    make(id=f"bm{i}", brand="Audi", model="rs3",
                         title="Audi RS3", fuel="essence", year=2020, price=45000)
                    for i in range(3)
                ]
            return [
                make(id=f"bo{i}", brand="Audi", model="a3",
                     title="Audi RS3 Sportback", fuel="essence", year=2020, price=46000)
                for i in range(25)
            ]

        monkeypatch.setattr(search_service, "PiloterrProvider",
                            _fake_provider_factory(url_to_listings))

        res = run_search("audi", "rs3", "essence", 2018, 2026)
        assert res.strategy == "elargie"
        # merge dédupliqué : 3 + 25 = 28 annonces brutes
        assert res.raw_count == 28
        assert len(res.listings) > 3

    def test_autre_marque_jamais_retenue(self, make, monkeypatch):
        # Le 2e appel ramène des BMW : elles ne doivent jamais entrer dans une reche Audi
        def url_to_listings(kind):
            if kind == "brand_model":
                return [
                    make(id=f"bm{i}", brand="Audi", model="rs3",
                         title="Audi RS3", fuel="essence", year=2020, price=45000)
                    for i in range(3)
                ]
            return [
                make(id=f"x{i}", brand="BMW", model="m3",
                     title="BMW M3 vs RS3", fuel="essence", year=2020, price=45000)
                for i in range(25)
            ]

        monkeypatch.setattr(search_service, "PiloterrProvider",
                            _fake_provider_factory(url_to_listings))

        res = run_search("audi", "rs3", "essence", 2018, 2026)
        assert all(l.brand.lower() == "audi" for l in res.listings)
