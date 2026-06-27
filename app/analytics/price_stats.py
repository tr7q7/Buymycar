import statistics
from typing import List
from app.models.listing import Listing


def compute_stats(listings: List[Listing]) -> dict:
    if not listings:
        return {"count": 0, "mean": 0, "median": 0, "min": 0, "max": 0, "stdev": 0}

    prices = [l.price for l in listings]
    return {
        "count": len(prices),
        "mean": round(statistics.mean(prices), 0),
        "median": round(statistics.median(prices), 0),
        "min": round(min(prices), 0),
        "max": round(max(prices), 0),
        "stdev": round(statistics.stdev(prices), 0) if len(prices) > 1 else 0,
    }
