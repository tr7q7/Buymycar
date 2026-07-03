"""
Catalogue — alimente les sélecteurs dépendants du frontend
(marque → modèles → carburants plausibles).

Wrappe directement le cœur métier existant (car_catalog, fuel_compat).
"""

from typing import List

from fastapi import APIRouter, Query

from app.utils.car_catalog import brands as catalog_brands, models_for
from app.utils.fuel_compat import fuels_for

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/brands", response_model=List[str])
def get_brands() -> List[str]:
    """Toutes les marques du catalogue, triées."""
    return sorted(catalog_brands())


@router.get("/models", response_model=List[str])
def get_models(brand: str = Query(..., examples=["Audi"])) -> List[str]:
    """Modèles disponibles pour une marque (label exact du catalogue)."""
    return models_for(brand)


@router.get("/fuels", response_model=List[str])
def get_fuels(
    brand: str = Query(..., examples=["Audi"]),
    model: str = Query("", examples=["RS3"]),
) -> List[str]:
    """Carburants plausibles pour une marque/modèle (essence, diesel, electrique)."""
    return fuels_for(brand, model)
