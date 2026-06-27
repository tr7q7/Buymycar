from typing import List
from app.models.listing import Listing


def clean(listings: List[Listing]) -> List[Listing]:
    seen_ids = set()
    result = []
    for l in listings:
        if l.id in seen_ids:
            continue
        if l.price <= 0 or l.mileage < 0 or l.year < 1990:
            continue
        seen_ids.add(l.id)
        result.append(l)
    return result
