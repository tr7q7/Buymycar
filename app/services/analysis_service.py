from typing import List
from app.models.listing import Listing
from app.analytics.price_stats import compute_stats
from app.analytics.outlier_detector import detect_outliers
from app.analytics.market_scorer import score_listings


def run_analysis(listings: List[Listing]) -> dict:
    # 1. Stats sur la liste brute pour détecter les outliers
    initial_stats = compute_stats(listings)
    # 2. Suppression des outliers
    listings = detect_outliers(listings, median_price=initial_stats["median"])
    # 3. Recalcul des stats sur la liste nettoyée — médiane plus représentative
    stats = compute_stats(listings)
    # 4. Score calculé avec la médiane post-nettoyage
    listings = score_listings(listings, median_price=stats["median"])
    return {"listings": listings, "stats": stats}
