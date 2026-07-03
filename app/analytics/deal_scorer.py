"""
Score de bonne affaire — échelle 0 à 100.

Trois composantes indépendantes :

  Prix vs marché estimé  60 pts  (source principale du score)
  Kilométrage            25 pts  (par rapport à la médiane de l'échantillon)
  Année                  15 pts  (position dans la plage de l'échantillon)

Calibration :
  Annonce typique (prix médian, km médian, année médiane)  → ~57 pts  "Prix correct"
  Bonne affaire  (−15 % marché, km faible, récente)        → ~80 pts  "Très intéressant"
  Excellente     (−30 % marché, km très faible, la + récente) → ~90+ pts
  Trop cher      (+30 % marché, km élevé, ancienne)        → ~20 pts  "Trop cher"

Barème :
  90–100  Excellente affaire
  75–89   Très intéressant
  55–74   Prix correct
  35–54   Peu intéressant
  < 35    Trop cher ou suspect
"""

import statistics
from typing import List, Optional

from app.models.listing import Listing
from app.analytics.market_price_estimator import MarketEstimate


# ── Constantes de calibration ─────────────────────────────────────────────────

# Prix : ratio price/market entre lequel le score prix est interpolé
_PRICE_BEST  = 0.60   # ratio → 60 pts (40 % sous le marché)
_PRICE_WORST = 1.50   # ratio → 0 pt  (50 % au-dessus)

# Kilométrage : ratio km/median_km
_KM_BEST  = 0.50   # ratio → 25 pts (moitié de la médiane)
_KM_WORST = 2.00   # ratio → 0 pt  (double de la médiane)

# Poids de chaque composante
_W_PRICE = 60
_W_KM    = 25
_W_YEAR  = 15


def _score_price(price: float, market_ref: float) -> float:
    """Score prix : 0–60 selon l'écart à la valeur de marché."""
    if market_ref <= 0:
        return _W_PRICE * 0.50   # neutre si pas de référence
    ratio = price / market_ref
    raw = ((_PRICE_WORST - ratio) / (_PRICE_WORST - _PRICE_BEST))
    return _W_PRICE * max(0.0, min(1.0, raw))


def _score_km(mileage: int, median_km: float) -> float:
    """Score kilométrage : 0–25 inversement proportionnel au ratio km/médiane."""
    if median_km <= 0:
        return _W_KM * 0.50
    ratio = mileage / median_km
    raw = ((_KM_WORST - ratio) / (_KM_WORST - _KM_BEST))
    return _W_KM * max(0.0, min(1.0, raw))


def _score_year(year: int, year_min: int, year_max: int) -> float:
    """Score année : 0–15 linéaire dans la plage de l'échantillon."""
    if year_max == year_min:
        return _W_YEAR * 0.50
    raw = (year - year_min) / (year_max - year_min)
    return _W_YEAR * max(0.0, min(1.0, raw))


def deal_score_listings(
    listings: List[Listing],
    stats: dict,
    market_est: Optional[MarketEstimate] = None,
) -> List[Listing]:
    """
    Calcule et affecte un score 0–100 à chaque annonce.

    market_est : résultat de estimate_market_price (peut être None).
    stats      : dict avec "median" (utilisé en fallback si market_est absent).
    """
    if not listings:
        return listings

    # Référence prix : valeur estimée pondérée > médiane brute
    market_ref = (
        market_est.estimated if market_est is not None
        else stats.get("median", 0.0)
    )

    # Statistiques de l'échantillon pour km et année
    mileages = [l.mileage for l in listings]
    years    = [l.year    for l in listings]

    median_km = statistics.median(mileages) if mileages else 0.0
    year_min  = min(years) if years else 0
    year_max  = max(years) if years else 0

    for listing in listings:
        s_price = _score_price(listing.price, market_ref)
        s_km    = _score_km(listing.mileage, median_km)
        s_year  = _score_year(listing.year, year_min, year_max)
        listing.score = round(s_price + s_km + s_year, 1)

    return listings


def score_label(score: float) -> str:
    """Libellé textuel du score."""
    if score is None:
        return "—"
    s = int(round(score))
    if s >= 90:
        return "Excellente affaire"
    if s >= 75:
        return "Très intéressant"
    if s >= 55:
        return "Prix correct"
    if s >= 35:
        return "Peu intéressant"
    return "Trop cher ou suspect"
