"""Root API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import Settings


def build_api_router(settings: Settings) -> APIRouter:
    root = APIRouter()
    # Sprint 1 contract: GET /health
    root.include_router(health_router)
    # Also expose under /api/v1 for API_SPEC path compatibility
    root.include_router(v1_router, prefix=settings.api_v1_prefix)
    return root
