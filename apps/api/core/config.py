"""
Configuration de l'API — lue depuis l'environnement.

Aucune valeur secrète en dur. PILOTERR_API_KEY reste géré par le cœur métier
(app.providers.piloterr_provider), pas ici.
"""

import os
from dataclasses import dataclass, field
from typing import List


def _origins_from_env() -> List[str]:
    """Origines CORS autorisées (front). Séparées par des virgules dans CORS_ORIGINS."""
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


@dataclass
class Settings:
    app_name: str = "AutoCote API"
    version: str = "0.1.0"
    cors_origins: List[str] = field(default_factory=_origins_from_env)


settings = Settings()
