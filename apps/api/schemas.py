"""
Schémas Pydantic — contrat d'entrée/sortie de l'API.

Découplent la représentation HTTP/JSON des dataclasses internes (Listing,
SearchResult…). Le frontend ne dépend que de ces schémas.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.services.search_service import SearchResult
from app.utils.formatting import clean_model_label, clean_title


# ── Entrée ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    brand: str = Field(..., examples=["audi"])
    model: str = Field("", examples=["rs3"])
    fuel: str = Field(..., examples=["essence"])
    year_min: int = Field(..., ge=1990, le=2100, examples=[2018])
    year_max: int = Field(..., ge=1990, le=2100, examples=[2026])


# ── Sortie ────────────────────────────────────────────────────────────────────

class ListingOut(BaseModel):
    id: str
    brand: str
    model: str
    year: int
    mileage: int
    price: float
    fuel: str
    transmission: str
    location: str
    score: Optional[float] = None
    title: str = ""
    url: str = ""
    image_url: str = ""


class StatsOut(BaseModel):
    count: int
    mean: float
    median: float
    min: float
    max: float
    stdev: float


class FilterOut(BaseModel):
    level: int
    strict_count: int
    retained: int
    year_min_used: int
    year_max_used: int


class MetaOut(BaseModel):
    total_results: int
    returned_results: int
    credits_used: int
    credits_remaining: int


class MarketEstimateOut(BaseModel):
    estimated: float          # valeur de marché estimée (€)
    low: float                # intervalle normal bas (P25 pondéré)
    high: float               # intervalle normal haut (P75 pondéré)
    confidence: str           # "Élevée" / "Moyenne" / "Faible"
    n_used: int               # nb d'annonces dans le calcul
    effective_n: float        # taille d'échantillon effective (ESS)


class SearchResultOut(BaseModel):
    listings: List[ListingOut]
    stats: StatsOut
    low_price_excluded: int
    strategy: str
    lbc_url: str
    raw_count: int
    filter: FilterOut
    meta: Optional[MetaOut] = None
    market_estimate: Optional[MarketEstimateOut] = None


# ── Job ───────────────────────────────────────────────────────────────────────

class JobCreatedOut(BaseModel):
    job_id: str
    status: str


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    result: Optional[SearchResultOut] = None
    error: Optional[str] = None


# ── Mapper interne → sortie ───────────────────────────────────────────────────

def to_search_result_out(res: SearchResult) -> SearchResultOut:
    """Convertit un SearchResult (dataclasses internes) en schéma de sortie."""
    meta_out = None
    if res.meta is not None:
        meta_out = MetaOut(
            total_results=res.meta.total_results,
            returned_results=res.meta.returned_results,
            credits_used=res.meta.credits_used,
            credits_remaining=res.meta.credits_remaining,
        )

    market_out = None
    if res.market_est is not None:
        market_out = MarketEstimateOut(
            estimated=res.market_est.estimated,
            low=res.market_est.low,
            high=res.market_est.high,
            confidence=res.market_est.confidence,
            n_used=res.market_est.n_used,
            effective_n=res.market_est.effective_n,
        )

    return SearchResultOut(
        listings=[
            ListingOut(
                id=l.id, brand=l.brand, model=clean_model_label(l.model), year=l.year,
                mileage=l.mileage, price=l.price, fuel=l.fuel,
                transmission=l.transmission, location=l.location,
                score=l.score, title=clean_title(l.title), url=l.url, image_url=l.image_url,
            )
            for l in res.listings
        ],
        stats=StatsOut(**res.stats),
        low_price_excluded=res.low_price_excluded,
        strategy=res.strategy,
        lbc_url=res.lbc_url,
        raw_count=res.raw_count,
        filter=FilterOut(
            level=res.filt.level,
            strict_count=res.filt.strict_count,
            retained=len(res.filt.listings),
            year_min_used=res.filt.year_min_used,
            year_max_used=res.filt.year_max_used,
        ),
        meta=meta_out,
        market_estimate=market_out,
    )
