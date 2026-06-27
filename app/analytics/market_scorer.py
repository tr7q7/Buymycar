from typing import List
from app.models.listing import Listing

# Ratio prix/médiane à partir duquel le score tombe à 0.
# Exemple : SCORE_FLOOR_RATIO = 2.0 → une annonce à 2× la médiane vaut 0/10.
SCORE_FLOOR_RATIO = 2.0

# Score attribué quand la médiane est indisponible (données insuffisantes).
SCORE_NEUTRAL = 5.0


def score_listings(listings: List[Listing], median_price: float) -> List[Listing]:
    """
    Attribue un score de 0 à 10 à chaque annonce selon son prix relatif à la médiane.

    Formule : score = 10 × (SCORE_FLOOR_RATIO - ratio)
      où ratio = prix / médiane

    Exemples :
      ratio = 0.0  → score = 10.0  (prix nul, théorique)
      ratio = 0.5  → score = 10.0  (plafonné — 50% sous la médiane)
      ratio = 1.0  → score =  5.0  (prix exact médian)
      ratio = 1.5  → score =  2.5  (50% au-dessus de la médiane)
      ratio = 2.0  → score =  0.0  (SCORE_FLOOR_RATIO atteint)
      ratio > 2.0  → score =  0.0  (plafonné à 0)
    """
    if median_price <= 0:
        for listing in listings:
            listing.score = SCORE_NEUTRAL
        return listings

    for listing in listings:
        ratio = listing.price / median_price
        raw_score = 10 * (SCORE_FLOOR_RATIO - ratio)
        listing.score = round(max(0.0, min(10.0, raw_score)), 1)

    return listings
