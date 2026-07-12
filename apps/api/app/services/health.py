"""Health / readiness service."""

from __future__ import annotations

import os
import time
from typing import Any

from sqlalchemy import text

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.health import HealthResponse, ReadyCheck, ReadyResponse

logger = get_logger(__name__)


def build_health_response(
    settings: Settings,
    *,
    uptime_seconds: float = 0.0,
) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        uptime_seconds=round(max(0.0, uptime_seconds), 3),
    )


async def _check_database(app: Any) -> ReadyCheck:
    started = time.perf_counter()
    engine = getattr(app.state, "engine", None)
    if engine is None:
        return ReadyCheck(name="database", status="error", detail="engine not configured")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ReadyCheck(
            name="database",
            status="ok",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:  # noqa: BLE001 — readiness must not raise
        logger.warning("ready_database_failed", error=str(exc))
        return ReadyCheck(
            name="database",
            status="error",
            detail="unavailable",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


async def _check_redis(settings: Settings) -> ReadyCheck:
    started = time.perf_counter()
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5)
        try:
            pong = await client.ping()
        finally:
            await client.aclose()
        if not pong:
            return ReadyCheck(name="redis", status="error", detail="ping failed")
        return ReadyCheck(
            name="redis",
            status="ok",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ready_redis_failed", error=str(exc))
        return ReadyCheck(
            name="redis",
            status="error",
            detail="unavailable",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )


def _provider_status() -> ReadyCheck:
    """Non-blocking: report whether a provider key is configured (no network call)."""
    configured = []
    if os.getenv("GEMINI_API_KEY", "").strip():
        configured.append("gemini")
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        configured.append("openrouter")
    if os.getenv("OPENAI_API_KEY", "").strip():
        configured.append("openai")
    if not configured:
        return ReadyCheck(
            name="ai_providers",
            status="degraded",
            detail="no provider API keys configured",
        )
    return ReadyCheck(
        name="ai_providers",
        status="ok",
        detail=",".join(configured),
    )


async def check_readiness(app: Any, settings: Settings) -> ReadyResponse:
    db = await _check_database(app)
    require_redis = settings.ready_require_redis or settings.ai_queue_backend == "redis"
    redis_check = await _check_redis(settings)
    providers = _provider_status()

    checks = [db, redis_check, providers]
    ready = db.status == "ok" and (not require_redis or redis_check.status == "ok")

    return ReadyResponse(
        status="ready" if ready else "not_ready",
        service=settings.app_name,
        version=settings.app_version,
        checks=checks,
    )
