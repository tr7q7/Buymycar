"""
Filet de sécurité — score de bonne affaire 0-100.

Fige la calibration : prix vs marché (60 pts) + kilométrage (25 pts) + année (15 pts),
ainsi que le barème de libellés.
"""

import pytest

from app.analytics.deal_scorer import deal_score_listings, score_label


class TestScoreLabel:
    @pytest.mark.parametrize("score, expected", [
        (95, "Excellente affaire"),
        (90, "Excellente affaire"),
        (89, "Très intéressant"),
        (75, "Très intéressant"),
        (74, "Prix correct"),
        (55, "Prix correct"),
        (54, "Peu intéressant"),
        (35, "Peu intéressant"),
        (34, "Trop cher ou suspect"),
        (0, "Trop cher ou suspect"),
    ])
    def test_bareme(self, score, expected):
        assert score_label(score) == expected

    def test_none(self):
        assert score_label(None) == "—"


class TestDealScore:
    def test_valeurs_calibrees(self, make):
        # Référence marché = médiane (market_est=None).
        # A : sous le marché, faible km, année récente → très intéressant
        # B : au-dessus, fort km, année ancienne → trop cher
        a = make(id="A", price=8000, mileage=50000, year=2020)
        b = make(id="B", price=12000, mileage=100000, year=2018)
        listings = deal_score_listings([a, b], stats={"median": 10000}, market_est=None)

        assert a.score == 83.9      # 46.67 (prix) + 22.22 (km) + 15 (année)
        assert b.score == 31.1      # 20.0  (prix) + 11.11 (km) + 0  (année)
        assert score_label(a.score) == "Très intéressant"
        assert score_label(b.score) == "Trop cher ou suspect"

    def test_prix_plus_bas_score_plus_haut(self, make):
        cheap = make(id="c", price=7000, mileage=60000, year=2019)
        expensive = make(id="e", price=15000, mileage=60000, year=2019)
        deal_score_listings([cheap, expensive], stats={"median": 10000})
        assert cheap.score > expensive.score

    def test_median_nulle_score_neutre_non_crashant(self, make):
        l = make(price=10000)
        deal_score_listings([l], stats={"median": 0}, market_est=None)
        # median=0 → prix neutre 30 ; une seule annonce → median_km = son propre km
        # (ratio 1.0 → 16.67) et année neutre 7.5. Total = 54.2. Surtout : pas de crash.
        assert l.score == 54.2

    def test_liste_vide(self):
        assert deal_score_listings([], stats={"median": 10000}) == []
