"""
Estimation de la durée de revente (jours).

Méthode MVP :
  Trois signaux indépendants, combinés en une durée estimée :

  1. Liquidité du marché  — nombre d'annonces comparables retenues.
     Plus il y en a, plus le marché est actif et la revente rapide.

  2. Positionnement prix  — rapport prix de l'annonce / prix médian.
     Un prix en dessous du médian part plus vite.

  3. Dispersion des prix  — coefficient de variation (std / mean).
     Forte dispersion = marché hétérogène = délai plus incertain.

La durée de base est interpolée entre 7 jours (marché très actif,
prix sous médian) et 90 jours (marché étroit, prix au-dessus).

Confiance :
  - Élevée  : ≥ 30 annonces et dispersion faible (CV < 0.25)
  - Moyenne : ≥ 15 annonces ou dispersion modérée
  - Faible  : < 15 annonces ou dispersion forte
"""

from dataclasses import dataclass


@dataclass
class ResaleEstimate:
    days: int
    confidence: str       # "Élevée" / "Moyenne" / "Faible"
    explanation: str


def estimate_resale_time(
    n_listings: int,
    median_price: float,
    mean_price: float,
    cv: float,
) -> ResaleEstimate:
    """
    n_listings   : nombre d'annonces comparables retenues après filtrage
    median_price : prix médian de l'échantillon
    mean_price   : prix moyen (utilisé pour le CV si non fourni)
    cv           : coefficient de variation (std / mean) de l'échantillon
    """
    # ── Facteur liquidité (0 à 1) ─────────────────────────────────────────────
    # 0 = marché très étroit (≤ 5 annonces), 1 = marché très actif (≥ 60)
    _liq = min(1.0, max(0.0, (n_listings - 5) / 55))

    # ── Facteur prix (0 à 1) ──────────────────────────────────────────────────
    # ratio prix/médian entre 0.7 (très bon prix) et 1.3 (cher)
    # → converti en avantage : 1.0 si très bon prix, 0.0 si trop cher
    if median_price > 0:
        _price_ratio = mean_price / median_price
    else:
        _price_ratio = 1.0
    _price_factor = min(1.0, max(0.0, (1.3 - _price_ratio) / 0.6))

    # ── Score combiné (0 à 1) ─────────────────────────────────────────────────
    # Liquidité pèse plus (marché actif > prix attractif)
    _score = 0.65 * _liq + 0.35 * _price_factor

    # ── Durée brute interpolée entre 7 et 90 jours ───────────────────────────
    _days_raw = 90 - _score * 83   # score=0 → 90 j, score=1 → 7 j
    days = max(7, min(90, int(round(_days_raw))))

    # ── Niveau de confiance ───────────────────────────────────────────────────
    if n_listings >= 30 and cv < 0.25:
        confidence = "Élevée"
    elif n_listings >= 15 or cv < 0.40:
        confidence = "Moyenne"
    else:
        confidence = "Faible"

    # ── Explication courte ────────────────────────────────────────────────────
    _parts = [f"Basé sur {n_listings} annonces comparables"]
    if cv >= 0.40:
        _parts.append("dispersion des prix élevée")
    elif cv < 0.20:
        _parts.append("marché homogène")
    if _price_ratio < 0.90:
        _parts.append("prix sous le médian — facteur accélérateur")
    elif _price_ratio > 1.15:
        _parts.append("prix au-dessus du médian — facteur ralentisseur")
    explanation = " · ".join(_parts) + "."

    return ResaleEstimate(days=days, confidence=confidence, explanation=explanation)
