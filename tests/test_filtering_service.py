"""
Filet de sécurité — filtrage progressif et correspondance de modèle.

Ces tests figent notamment la correction Audi RS3 : un modèle sportif dont
le champ `model` LBC diffère du nom commercial doit être rattrapé via le titre,
SANS jamais accepter une autre marque ni un modèle de base non apparenté.
"""

from app.services.filtering_service import (
    is_model_match,
    progressive_filter,
    _model_loose,
    _model_strict,
)


# ── is_model_match ────────────────────────────────────────────────────────────

class TestIsModelMatch:
    def test_match_sur_champ_model_structure(self, make):
        l = make(brand="Renault", model="Clio", title="Renault Clio 5")
        assert is_model_match(l, "clio") is True

    def test_rs3_encode_a3_rattrape_par_titre(self, make):
        # LBC encode souvent la RS3 avec model="a3" ; le titre contient "RS3"
        l = make(brand="Audi", model="a3", title="AUDI RS3 Sportback 400ch")
        assert is_model_match(l, "rs3") is True

    def test_rs3_avec_espace_dans_titre(self, make):
        # "RS 3" dans le titre doit matcher "rs3" (normalisation espaces/tirets)
        l = make(brand="Audi", model="rs_3", title="Audi RS 3 Berline 2.5 TFSI")
        assert is_model_match(l, "rs3") is True

    def test_rs3_champ_model_vide_rattrape_par_titre(self, make):
        l = make(brand="Audi", model="", title="Audi RS3 Competition Plus")
        assert is_model_match(l, "rs3") is True

    def test_a3_standard_nest_pas_une_rs3(self, make):
        # Faux positif à éviter absolument
        l = make(brand="Audi", model="a3", title="Audi A3 Sportback 35 TFSI")
        assert is_model_match(l, "rs3") is False

    def test_golf_gti_rattrape_par_titre(self, make):
        l = make(brand="Volkswagen", model="golf", title="Volkswagen Golf GTI 245ch")
        assert is_model_match(l, "Golf GTI") is True

    def test_golf_standard_nest_pas_une_gti(self, make):
        l = make(brand="Volkswagen", model="golf", title="Volkswagen Golf 1.5 TSI")
        assert is_model_match(l, "Golf GTI") is False

    def test_modele_vide_matche_tout(self, make):
        l = make(brand="Audi", model="a3", title="Audi A3")
        assert is_model_match(l, "") is True


# ── progressive_filter — marque jamais élargie ────────────────────────────────

class TestBrandNeverExpanded:
    def test_autre_marque_toujours_rejetee_meme_si_titre_matche(self, make):
        # Une BMW dont le titre contient "RS3" ne doit JAMAIS entrer dans une
        # recherche Audi RS3.
        listings = [
            make(id=str(i), brand="BMW", model="m3",
                 title="BMW M3 vs Audi RS3 comparatif", fuel="essence", year=2020)
            for i in range(30)
        ]
        result = progressive_filter(
            listings, brand="audi", model="rs3", fuel="essence",
            year_min=2018, year_max=2026,
        )
        assert result.listings == []
        assert all(l.brand.lower() == "audi" for l in result.listings)


# ── progressive_filter — niveaux ──────────────────────────────────────────────

class TestProgressiveLevels:
    def test_niveau_1_quand_echantillon_strict_suffisant(self, make):
        listings = [
            make(id=str(i), brand="Renault", model="Clio",
                 title="Renault Clio", fuel="diesel", year=2020)
            for i in range(25)
        ]
        result = progressive_filter(
            listings, brand="renault", model="clio", fuel="diesel",
            year_min=2018, year_max=2021,
        )
        assert result.level == 1
        assert result.strict_count == 25
        assert len(result.listings) == 25
        assert result.year_min_used == 2018
        assert result.year_max_used == 2021

    def test_niveau_2_elargit_annee_de_plus_moins_1(self, make):
        # 25 Clio mais toutes en 2017 (hors plage 2018-2021) → strict=0,
        # rattrapées au niveau 2 via année ±1
        listings = [
            make(id=str(i), brand="Renault", model="Clio",
                 title="Renault Clio", fuel="diesel", year=2017)
            for i in range(25)
        ]
        result = progressive_filter(
            listings, brand="renault", model="clio", fuel="diesel",
            year_min=2018, year_max=2021,
        )
        assert result.level == 2
        assert result.strict_count == 0
        assert result.year_min_used == 2017  # 2018 - 1

    def test_niveau_3_rs3_via_titre(self, make):
        # Échantillon RS3 encodé model="a3" → niveaux 1/2 via is_model_match,
        # niveau 3 atteint faute de volume mais RS3 correctement retenues.
        listings = [
            make(id=str(i), brand="Audi", model="a3",
                 title="AUDI RS3 Sportback 400ch", fuel="essence", year=2020)
            for i in range(10)
        ]
        result = progressive_filter(
            listings, brand="audi", model="rs3", fuel="essence",
            year_min=2018, year_max=2026,
        )
        assert len(result.listings) == 10
        assert all("RS3" in l.title.upper() for l in result.listings)

    def test_carburant_exact_respecte(self, make):
        listings = (
            [make(id=f"d{i}", brand="Renault", model="Clio",
                  fuel="diesel", year=2020) for i in range(15)]
            + [make(id=f"e{i}", brand="Renault", model="Clio",
                    fuel="essence", year=2020) for i in range(15)]
        )
        result = progressive_filter(
            listings, brand="renault", model="clio", fuel="diesel",
            year_min=2018, year_max=2021,
        )
        assert all(l.fuel == "diesel" for l in result.listings)


# ── helpers de correspondance ─────────────────────────────────────────────────

class TestModelHelpers:
    def test_strict_substring(self):
        assert _model_strict("clio", "Clio 5") is True
        assert _model_strict("308", "3008") is False

    def test_loose_intersection_de_mots(self):
        assert _model_loose("Yaris Cross", "Yaris") is True
        assert _model_loose("308", "3008") is False
