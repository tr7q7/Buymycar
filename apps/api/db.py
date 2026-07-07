"""
Couche base de données — SQLAlchemy 2.0.

Un seul code pour deux backends via DATABASE_URL :
  - local  : SQLite (défaut sqlite:///./autocote.db)
  - Render : Postgres (postgresql://…)

Les URLs Render de la forme "postgres://…" sont normalisées en "postgresql://…"
(dialecte attendu par SQLAlchemy).
"""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip() or "sqlite:///./autocote.db"
    # Render fournit "postgres://" ; SQLAlchemy attend "postgresql://".
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _database_url()

# check_same_thread=False : nécessaire car FastAPI + JobManager utilisent plusieurs threads.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles ORM."""


def init_db() -> None:
    """Crée les tables si elles n'existent pas. Importe les modèles au passage."""
    from apps.api import db_models  # noqa: F401 — enregistre les tables sur Base
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : fournit une session, fermée en fin de requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
