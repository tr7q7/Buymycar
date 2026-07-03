from typing import List, Tuple
from app.models.listing import Listing

# Prix > 3× médiane = annonce aberrante haute (exclue des stats)
_OUTLIER_RATIO = 3.0

# Prix < 60 % médiane = annonce aberrante basse (accidentés, pièces, arnaques…)
_LOW_PRICE_RATIO = 0.60


def detect_outliers(listings: List[Listing], median_price: float) -> List[Listing]:
    if median_price <= 0:
        return listings
    threshold = median_price * _OUTLIER_RATIO
    return [l for l in listings if l.price <= threshold]


def exclude_low_prices(listings: List[Listing], median_price: float) -> Tuple[List[Listing], int]:
    """
    Exclut les annonces dont le prix est inférieur à 60 % de la médiane.
    Retourne (liste conservée, nombre d'annonces exclues).
    """
    if median_price <= 0:
        return listings, 0
    threshold = median_price * _LOW_PRICE_RATIO
    kept = [l for l in listings if l.price >= threshold]
    return kept, len(listings) - len(kept)
