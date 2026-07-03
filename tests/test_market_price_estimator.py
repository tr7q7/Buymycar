"""
Filet de sécurité — estimation du prix de marché (pondération gaussienne).
"""

from app.analytics.market_price_estimator import estimate_market_price


class TestEstimateMarketPrice:
    def test_moins_de_3_annonces_retourne_none(self, make):
        listings = [make(id="1"), make(id="2")]
        assert estimate_market_price(listings) is None

    def test_profils_identiques_moyenne_simple(self, make):
        # Trois annonces même année / même km → poids égaux → moyenne arithmétique
        listings = [
            make(id="1", price=10000, year=2020, mileage=60000),
            make(id="2", price=12000, year=2020, mileage=60000),
            make(id="3", price=14000, year=2020, mileage=60000),
        ]
        est = estimate_market_price(listings)
        assert est is not None
        assert est.estimated == 12000
        assert est.low == 10000       # P25 pondéré
        assert est.high == 14000      # P75 pondéré
        assert est.n_used == 3

    def test_confiance_faible_sur_petit_echantillon(self, make):
        listings = [
            make(id="1", price=10000, year=2020, mileage=60000),
            make(id="2", price=12000, year=2020, mileage=60000),
            make(id="3", price=14000, year=2020, mileage=60000),
        ]
        est = estimate_market_price(listings)
        # ESS = 3 (< 8) → confiance "Faible"
        assert est.confidence == "Faible"

    def test_prix_positif(self, make):
        listings = [make(id=str(i), price=9000 + i * 500) for i in range(10)]
        est = estimate_market_price(listings)
        assert est.estimated > 0
        assert est.low <= est.estimated <= est.high
