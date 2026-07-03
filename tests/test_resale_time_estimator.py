"""
Filet de sécurité — durée estimée de revente.
"""

from app.analytics.resale_time_estimator import estimate_resale_time


class TestEstimateResaleTime:
    def test_marche_actif_prix_correct(self):
        r = estimate_resale_time(n_listings=47, median_price=8000, mean_price=7600, cv=0.22)
        assert r.days == 32
        assert r.confidence == "Élevée"
        assert "47 annonces" in r.explanation

    def test_marche_etroit_disperse(self):
        r = estimate_resale_time(n_listings=8, median_price=8000, mean_price=9200, cv=0.52)
        assert r.days == 80
        assert r.confidence == "Faible"
        assert "dispersion" in r.explanation.lower()

    def test_duree_bornee_7_a_90(self):
        rapide = estimate_resale_time(n_listings=200, median_price=8000, mean_price=5000, cv=0.10)
        lent = estimate_resale_time(n_listings=1, median_price=8000, mean_price=12000, cv=0.9)
        assert 7 <= rapide.days <= 90
        assert 7 <= lent.days <= 90
        assert rapide.days < lent.days

    def test_confiance_moyenne(self):
        r = estimate_resale_time(n_listings=20, median_price=8000, mean_price=8000, cv=0.30)
        assert r.confidence == "Moyenne"
