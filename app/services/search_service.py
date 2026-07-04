"""
Service de recherche — orchestration métier d'une analyse d'annonces.

Extrait de main.py (couche UI Streamlit) pour être réutilisable par n'importe
quel client : Streamlit aujourd'hui, API FastAPI demain.

Ce module ne connaît AUCUNE dépendance d'interface (pas de streamlit).
Il enchaîne : construction requête → appel Piloterr → stratégie duale
(brand+model puis brand-only si l'échantillon strict est trop faible) →
filtrage progressif → nettoyage → analyse (stats, scores, exclusions).

Les exceptions Piloterr (PiloterrServerError, PiloterrTimeoutError, PiloterrError)
remontent telles quelles : c'est au client (UI/API) de les présenter.
"""

from dataclasses import dataclass
from typing import List, Optional

from app.providers.piloterr_provider import SearchParams, PiloterrProvider, PiloterrMeta
from app.providers.leboncoin_query_builder import LeboncoinQueryBuilder
from app.services.cleaning_service import clean
from app.services.analysis_service import run_analysis
from app.services.filtering_service import progressive_filter, FilterResult
from app.analytics.market_price_estimator import MarketEstimate
from app.models.listing import Listing

# Seuil d'annonces strictement comparables en dessous duquel on tente la
# recherche élargie (marque seule).
_EXPAND_THRESHOLD = 20


@dataclass
class SearchResult:
    """Résultat complet d'une recherche, indépendant de toute UI."""
    listings: List[Listing]        # annonces retenues, nettoyées et scorées
    stats: dict                    # statistiques de prix post-nettoyage
    low_price_excluded: int        # nb d'annonces exclues (prix aberrant bas)
    filt: FilterResult             # détail du filtrage progressif (niveau, années…)
    meta: Optional[PiloterrMeta]   # métadonnées Piloterr (crédits, total…)
    lbc_url: str                   # URL LeBonCoin de la stratégie principale
    raw_count: int                 # nb d'annonces brutes récupérées (après merge éventuel)
    strategy: str                  # "standard" ou "elargie"
    market_est: Optional[MarketEstimate] = None  # valeur marché estimée (pondérée)


def run_search(
    brand: str,
    model: str,
    fuel: str,
    year_min: int,
    year_max: int,
) -> SearchResult:
    """
    Exécute une recherche complète et renvoie un SearchResult structuré.

    Comportement identique à l'ancien _fetch_piloterr de main.py.
    """
    params = SearchParams(
        brand=brand,
        model=model or None,
        fuel=fuel or None,
        year_min=year_min,
        year_max=year_max,
    )
    builder = LeboncoinQueryBuilder(params)

    # ── Stratégie 1 : brand + model ──────────────────────────────────────────
    lbc_url = builder.build()
    provider = PiloterrProvider(search_params=params, lbc_url=lbc_url)
    raw_listings, meta = provider.fetch_with_meta()
    raw_count = len(raw_listings)

    filt = progressive_filter(raw_listings, brand, model or "", fuel or "", year_min, year_max)
    strategy = "standard"

    # ── Stratégie 2 : brand seule (si échantillon strict insuffisant) ─────────
    if model and filt.strict_count < _EXPAND_THRESHOLD:
        params_brand = SearchParams(brand=brand, model=None, fuel=fuel or None,
                                    year_min=year_min, year_max=year_max)
        lbc_url_brand = LeboncoinQueryBuilder(params_brand).build()
        provider2 = PiloterrProvider(search_params=params, lbc_url=lbc_url_brand)
        raw2, _meta2 = provider2.fetch_with_meta()

        # Fusion des deux résultats (déduplication par id)
        seen_ids = {l.id for l in raw_listings}
        merged = raw_listings + [l for l in raw2 if l.id not in seen_ids]

        filt_merged = progressive_filter(merged, brand, model or "", fuel or "", year_min, year_max)

        if len(filt_merged.listings) > len(filt.listings):
            raw_listings = merged
            raw_count    = len(merged)
            filt         = filt_merged
            strategy     = "elargie"

    cleaned = clean(filt.listings)
    result  = run_analysis(cleaned)

    return SearchResult(
        listings=result["listings"],
        stats=result["stats"],
        low_price_excluded=result.get("low_price_excluded", 0),
        filt=filt,
        meta=meta,
        lbc_url=lbc_url,
        raw_count=raw_count,
        strategy=strategy,
        market_est=result.get("market_est"),
    )
