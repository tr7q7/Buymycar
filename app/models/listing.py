from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    id: str
    brand: str
    model: str
    year: int
    mileage: int        # km
    price: float        # EUR
    fuel: str           # essence, diesel, electrique, hybride
    transmission: str   # manuelle, automatique
    location: str
    source: str         # csv, mock, api...
    score: Optional[float] = field(default=None)  # score bonne affaire, calculé a posteriori
