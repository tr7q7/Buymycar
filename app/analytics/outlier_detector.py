from typing import List
from app.models.listing import Listing

# Annonce considérée aberrante si son prix dépasse 3x la médiane
_OUTLIER_RATIO = 3.0


def detect_outliers(listings: List[Listing], median_price: float) -> List[Listing]:
    if median_price <= 0:
        return listings
    threshold = median_price * _OUTLIER_RATIO
    return [l for l in listings if l.price <= threshold]
