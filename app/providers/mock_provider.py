import random
import uuid
from typing import List
from app.providers.base_provider import BaseProvider
from app.models.listing import Listing

_BRANDS = {
    "Renault": ["Clio", "Megane", "Captur", "Zoe"],
    "Peugeot": ["208", "308", "3008", "508"],
    "Volkswagen": ["Golf", "Polo", "Tiguan", "Passat"],
    "BMW": ["Serie 1", "Serie 3", "Serie 5", "X3"],
    "Toyota": ["Yaris", "Corolla", "RAV4", "CH-R"],
}

_FUELS = ["essence", "diesel", "electrique", "hybride"]
_TRANSMISSIONS = ["manuelle", "automatique"]
_LOCATIONS = ["Paris", "Lyon", "Marseille", "Bordeaux", "Lille", "Toulouse", "Nantes"]

# Prix de base approximatif par marque (EUR)
_BASE_PRICE = {
    "Renault": 12000,
    "Peugeot": 13000,
    "Volkswagen": 15000,
    "BMW": 22000,
    "Toyota": 16000,
}


class MockProvider(BaseProvider):
    def __init__(self, n: int = 120, seed: int = 42):
        self.n = n
        self.seed = seed

    def fetch(self) -> List[Listing]:
        rng = random.Random(self.seed)
        listings = []

        for _ in range(self.n):
            brand = rng.choice(list(_BRANDS.keys()))
            model = rng.choice(_BRANDS[brand])
            year = rng.randint(2010, 2024)
            mileage = rng.randint(0, 200000)
            age = 2024 - year

            base = _BASE_PRICE[brand]
            # Prix décroît avec l'âge et le kilométrage, avec bruit aléatoire
            price = base * (0.95 ** age) * (1 - mileage / 600000)
            price = max(1500, price * rng.uniform(0.80, 1.20))
            price = round(price / 100) * 100

            listings.append(Listing(
                id=str(uuid.uuid4()),
                brand=brand,
                model=model,
                year=year,
                mileage=mileage,
                price=price,
                fuel=rng.choice(_FUELS),
                transmission=rng.choice(_TRANSMISSIONS),
                location=rng.choice(_LOCATIONS),
                source="mock",
            ))

        return listings
