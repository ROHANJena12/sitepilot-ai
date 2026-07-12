"""FastAPI application factory."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import build_api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.startup import ConfigurationError, validate_settings
from app.db.database import create_engine, create_session_factory
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.timing import RequestTimingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    try:
        validate_settings(settings)
    except ConfigurationError as exc:
        logger.error("startup_configuration_invalid", error=str(exc))
        raise

    app.state.started_at = time.time()
    logger.info(
        "startup",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment.value,
        rate_limit_enabled=settings.rate_limit_enabled,
        security_headers_enabled=settings.security_headers_enabled,
        hsts_enabled=settings.hsts_enabled,
    )
    yield
    engine = getattr(app.state, "engine", None)
    if engine is not None:
        await engine.dispose()
        logger.info("shutdown", service=settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved = settings or get_settings()
    if resolved.is_testing:
        resolved = resolved.model_copy(update={"rate_limit_enabled": False})

    configure_logging(resolved)

    app = FastAPI(
        title="SitePilot AI API",
        version=resolved.app_version,
        debug=resolved.debug and not resolved.is_production,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.started_at = time.time()

    engine = create_engine(resolved)
    session_factory = create_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
            "X-Generation-ID",
            "X-AI-Feature",
            "X-AI-Cached",
            "X-AI-Provider",
            "X-AI-Model",
        ],
    )
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=resolved)
    app.add_middleware(SecurityHeadersMiddleware, settings=resolved)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    app.include_router(build_api_router(resolved))

    return app


app = create_app()
