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
    source: str         # csv, mock, piloterr-leboncoin...
    score: Optional[float] = field(default=None)   # score bonne affaire, calculé a posteriori
    title: str = field(default="")                 # titre de l'annonce
    url: str = field(default="")                   # lien vers l'annonce originale
    published_at: str = field(default="")          # date de publication (ISO 8601 ou chaîne brute)
    image_url: str = field(default="")             # URL image principale (small, ~400px)
