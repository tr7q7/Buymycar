"""
Fixtures et fabriques partagées pour la suite de tests.

Ces tests figent le comportement métier ACTUEL avant la migration SaaS
(FastAPI + Next.js). Toute régression sur les analytics ou le filtrage
doit faire échouer un test ici.
"""

import pytest

from app.models.listing import Listing


def make_listing(
    *,
    id: str = "1",
    brand: str = "Renault",
    model: str = "Clio",
    year: int = 2020,
    mileage: int = 60000,
    price: float = 12000.0,
    fuel: str = "diesel",
    transmission: str = "manuelle",
    location: str = "Paris",
    source: str = "test",
    title: str = "",
    url: str = "",
) -> Listing:
    """Fabrique un Listing avec des valeurs par défaut plausibles.

    Tous les champs sont surchargeables par mot-clé pour construire
    des scénarios précis sans bruit.
    """
    return Listing(
        id=id,
        brand=brand,
        model=model,
        year=year,
        mileage=mileage,
        price=price,
        fuel=fuel,
        transmission=transmission,
        location=location,
        source=source,
        title=title or f"{brand} {model}",
        url=url,
    )


@pytest.fixture
def make():
    """Expose la fabrique aux tests sous forme de fixture."""
    return make_listing
