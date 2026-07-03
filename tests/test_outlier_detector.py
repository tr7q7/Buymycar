"""
Filet de sécurité — exclusion des prix aberrants (hauts et bas).
"""

from app.analytics.outlier_detector import detect_outliers, exclude_low_prices


class TestDetectOutliers:
    def test_exclut_au_dessus_de_3x_mediane(self, make):
        listings = [
            make(id="ok", price=10000),
            make(id="haut", price=40000),   # > 3 × 10000
        ]
        kept = detect_outliers(listings, median_price=10000)
        assert [l.id for l in kept] == ["ok"]

    def test_conserve_a_exactement_3x(self, make):
        listings = [make(id="limite", price=30000)]
        kept = detect_outliers(listings, median_price=10000)
        assert len(kept) == 1

    def test_mediane_nulle_retourne_tout(self, make):
        listings = [make(id="1", price=99999)]
        assert detect_outliers(listings, median_price=0) == listings


class TestExcludeLowPrices:
    def test_exclut_sous_60pct_mediane(self, make):
        listings = [
            make(id="ok", price=10000),
            make(id="bas", price=5000),   # < 60 % de 10000
        ]
        kept, excluded = exclude_low_prices(listings, median_price=10000)
        assert [l.id for l in kept] == ["ok"]
        assert excluded == 1

    def test_conserve_a_exactement_60pct(self, make):
        listings = [make(id="limite", price=6000)]
        kept, excluded = exclude_low_prices(listings, median_price=10000)
        assert len(kept) == 1
        assert excluded == 0

    def test_mediane_nulle_retourne_tout(self, make):
        listings = [make(id="1", price=100)]
        kept, excluded = exclude_low_prices(listings, median_price=0)
        assert kept == listings
        assert excluded == 0
