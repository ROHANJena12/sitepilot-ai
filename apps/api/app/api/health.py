"""Health / readiness endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response, status

from app.dependencies.settings import SettingsDep
from app.schemas.health import HealthResponse, ReadyResponse
from app.services.health import build_health_response, check_readiness

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness health check",
)
async def health(request: Request, settings: SettingsDep) -> HealthResponse:
    """Process liveness — no dependency checks (use /ready for that)."""
    started_at = getattr(request.app.state, "started_at", None)
    uptime = time.time() - started_at if isinstance(started_at, (int, float)) else 0.0
    return build_health_response(settings, uptime_seconds=uptime)


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness check",
    responses={503: {"description": "Dependency not ready"}},
)
async def ready(
    request: Request,
    settings: SettingsDep,
    response: Response,
) -> ReadyResponse:
    """
    Dependency readiness for orchestration.

    Checks Postgres (required). Redis is required when ``READY_REQUIRE_REDIS=true``
    or ``AI_QUEUE_BACKEND=redis``. Provider probes are non-blocking metadata only.
    """
    payload = await check_readiness(request.app, settings)
    if payload.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return payload
