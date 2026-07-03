"""
Estimation du prix de marché par pondération gaussienne.

Principe :
  Chaque annonce reçoit un poids proportionnel à sa proximité (en année et kilométrage)
  avec le point de référence (médiane de l'échantillon). Les annonces les plus "typiques"
  ont donc le plus d'influence sur l'estimation.

Formule de poids :
  d = sqrt( (Δannée / σ_année)² + (Δkm / σ_km)² )
  w = exp(-d)          → 1 pour une annonce identique au point de référence
                       → proche de 0 pour une annonce très atypique

Intervalle normal = percentiles 25–75 pondérés (robuste aux distributions asymétriques).

Taille d'échantillon effective (ESS) :
  ESS = (Σw)² / Σ(w²)  → nombre "réel" d'annonces bien représentatives
"""

import math
import statistics
from dataclasses import dataclass
from typing import List

from app.models.listing import Listing


@dataclass
class MarketEstimate:
    estimated: float       # valeur de marché pondérée (€)
    low: float             # intervalle normal bas (percentile 25 pondéré)
    high: float            # intervalle normal haut (percentile 75 pondéré)
    n_used: int            # nombre d'annonces dans le calcul
    effective_n: float     # taille d'échantillon effective (ESS)
    confidence: str        # "Élevée" / "Moyenne" / "Faible"
    cv: float              # coefficient de variation (dispersion relative)


def _weighted_quantile(values: list, weights: list, q: float) -> float:
    """Percentile pondéré par tri + cumul des poids."""
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total = sum(weights)
    target = q * total
    cumul = 0.0
    for v, w in pairs:
        cumul += w
        if cumul >= target:
            return v
    return pairs[-1][0]


def estimate_market_price(
    listings: List[Listing],
    target_year: float | None = None,
    target_mileage: float | None = None,
) -> MarketEstimate | None:
    """
    Estime le prix de marché pour l'échantillon fourni.

    target_year / target_mileage : point de référence du calcul.
    Si None, utilise la médiane de l'échantillon (profil "voiture typique").
    """
    if len(listings) < 3:
        return None

    prices   = [l.price    for l in listings]
    years    = [l.year     for l in listings]
    mileages = [l.mileage  for l in listings]

    # ── Point de référence ────────────────────────────────────────────────────
    ref_year    = target_year    or statistics.median(years)
    ref_mileage = target_mileage or statistics.median(mileages)

    # ── Échelles de normalisation (au moins 2 ans et 20 000 km) ──────────────
    year_scale = max(2.0, statistics.stdev(years))    if len(years)    > 1 else 2.0
    km_scale   = max(20_000.0, statistics.stdev(mileages) * 0.5) if len(mileages) > 1 else 20_000.0

    # ── Calcul des poids gaussiens ────────────────────────────────────────────
    weights = []
    for l in listings:
        d_year = (l.year    - ref_year)    / year_scale
        d_km   = (l.mileage - ref_mileage) / km_scale
        w = math.exp(-(d_year ** 2 + d_km ** 2))
        weights.append(max(w, 1e-9))   # plancher pour éviter les poids nuls

    total_w = sum(weights)

    # ── Valeur estimée (moyenne pondérée) ────────────────────────────────────
    estimated = sum(p * w for p, w in zip(prices, weights)) / total_w

    # ── Intervalle normal (percentiles 25–75 pondérés) ───────────────────────
    low  = _weighted_quantile(prices, weights, 0.25)
    high = _weighted_quantile(prices, weights, 0.75)

    # ── Taille d'échantillon effective (ESS) ─────────────────────────────────
    ess = total_w ** 2 / sum(w ** 2 for w in weights)

    # ── Coefficient de variation (dispersion relative) ───────────────────────
    variance = sum(w * (p - estimated) ** 2 for p, w in zip(prices, weights)) / total_w
    std = math.sqrt(variance)
    cv  = std / estimated if estimated > 0 else 1.0

    # ── Niveau de confiance ───────────────────────────────────────────────────
    if ess >= 20 and cv < 0.25:
        confidence = "Élevée"
    elif ess >= 8 and cv < 0.45:
        confidence = "Moyenne"
    else:
        confidence = "Faible"

    return MarketEstimate(
        estimated   = round(estimated),
        low         = round(max(0.0, low)),
        high        = round(high),
        n_used      = len(listings),
        effective_n = round(ess, 1),
        confidence  = confidence,
        cv          = round(cv, 3),
    )
