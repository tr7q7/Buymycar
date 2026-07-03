"""Sonde de vie — utilisée par Render et le monitoring."""

from fastapi import APIRouter

from apps.api.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.version}
