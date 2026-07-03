from typing import List
from app.models.listing import Listing
from app.analytics.price_stats import compute_stats
from app.analytics.outlier_detector import detect_outliers, exclude_low_prices
from app.analytics.market_price_estimator import estimate_market_price
from app.analytics.deal_scorer import deal_score_listings


def run_analysis(listings: List[Listing]) -> dict:
    # 1. Stats brutes pour obtenir une première médiane
    initial_stats = compute_stats(listings)

    # 2. Exclusion des prix aberrants bas (< 60 % médiane) — véhicules accidentés, pièces, etc.
    listings, low_price_excluded = exclude_low_prices(listings, initial_stats["median"])

    # 3. Stats recalculées après exclusion basse
    stats_mid = compute_stats(listings)

    # 4. Exclusion des outliers hauts (> 3× médiane)
    listings = detect_outliers(listings, median_price=stats_mid["median"])

    # 5. Stats finales sur la liste nettoyée — médiane représentative du marché
    stats = compute_stats(listings)

    # 6. Estimation prix de marché pondérée (Gaussienne)
    market_est = estimate_market_price(listings)

    # 7. Score composite 0–100 (prix vs marché, km, année)
    listings = deal_score_listings(listings, stats, market_est)

    return {
        "listings": listings,
        "stats": stats,
        "low_price_excluded": low_price_excluded,
        "market_est": market_est,
    }
