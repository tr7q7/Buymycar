"""
Point d'entrée FastAPI.

Lancement local :
    uvicorn apps.api.main:app --reload

L'API wrappe le cœur métier Python existant (app.*). Aucune logique métier ici :
uniquement le câblage HTTP, la config CORS et l'enregistrement des routes.
"""

import sys
from pathlib import Path

# Racine du repo dans sys.path pour importer le cœur métier "app.*"
# quel que soit le répertoire de lancement.
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.core.config import settings
from apps.api.db import init_db
from apps.api.routers import health, catalog, search, credits


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crée les tables (crédits / paiements / recherches) au démarrage.
    init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(catalog.router)
app.include_router(search.router)
app.include_router(credits.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs"}
