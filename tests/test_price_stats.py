"""
Filet de sécurité — statistiques de prix.
"""

from app.analytics.price_stats import compute_stats


class TestComputeStats:
    def test_liste_vide_retourne_zeros(self):
        stats = compute_stats([])
        assert stats == {"count": 0, "mean": 0, "median": 0, "min": 0, "max": 0, "stdev": 0}

    def test_valeurs_connues(self, make):
        listings = [
            make(id="1", price=10000),
            make(id="2", price=12000),
            make(id="3", price=14000),
        ]
        stats = compute_stats(listings)
        assert stats["count"] == 3
        assert stats["median"] == 12000
        assert stats["mean"] == 12000
        assert stats["min"] == 10000
        assert stats["max"] == 14000

    def test_stdev_zero_sur_un_seul_element(self, make):
        stats = compute_stats([make(price=10000)])
        assert stats["stdev"] == 0
