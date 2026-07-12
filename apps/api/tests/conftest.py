"""Pytest configuration and fixtures."""

from __future__ import annotations

import os

# Must run before app settings classes instantiate — skip local .env leakage.
os.environ["SITEPILOT_TESTING"] = "1"

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Environment, Settings, clear_settings_cache
from app.db.base import Base
from app.main import create_app
from app.models import (  # noqa: F401 — register metadata
    AIGeneration,
    AIGenerationJob,
    AuditFinding,
    AuditRun,
    EngineExecution,
    HealthScore,
    Organization,
    Project,
    RecommendationRow,
    RecommendationSource,
    Report,
    Website,
)


def _test_database_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://sitepilot:sitepilot@localhost:5434/sitepilot_test",
    )


@pytest.fixture(scope="session", autouse=True)
def _isolate_local_dotenv_ai_defaults() -> None:
    """
    Prevent local ``apps/api/.env`` keys from flipping provider selection.

    Product default is Gemini (Sprint 30.6). Clear provider API keys so the
    cascade does not accidentally call real upstreams during the suite.
    """
    os.environ["AI_DEFAULT_PROVIDER"] = "gemini"
    for key in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        os.environ.pop(key, None)


@pytest.fixture()
def settings() -> Settings:
    clear_settings_cache()
    return Settings(
        app_name="sitepilot-api",
        app_version="0.1.0",
        environment=Environment.TESTING,
        debug=False,
        log_level="WARNING",
        database_url=_test_database_url(),
        cors_origins=["http://localhost:3000"],
        secret_key="test-secret",
    )


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    clear_settings_cache()


async def _prepare_database(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        # Partial unique indexes from DATABASE_SPEC (create_all may miss postgresql_where)
        await conn.execute(text("DROP INDEX IF EXISTS organizations_slug_uidx"))
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX organizations_slug_uidx "
                "ON organizations (slug) WHERE deleted_at IS NULL"
            )
        )
        await conn.execute(text("DROP INDEX IF EXISTS projects_org_slug_uidx"))
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX projects_org_slug_uidx "
                "ON projects (organization_id, slug) WHERE deleted_at IS NULL"
            )
        )
        await conn.execute(text("DROP INDEX IF EXISTS websites_project_canonical_uidx"))
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX websites_project_canonical_uidx "
                "ON websites (project_id, canonical_url) WHERE deleted_at IS NULL"
            )
        )
        await conn.execute(text("DROP INDEX IF EXISTS websites_canonical_trgm_idx"))
        await conn.execute(
            text(
                "CREATE INDEX websites_canonical_trgm_idx "
                "ON websites USING GIN (canonical_url gin_trgm_ops)"
            )
        )
        await conn.execute(text("DROP INDEX IF EXISTS audit_runs_website_created_idx"))
        await conn.execute(
            text(
                "CREATE INDEX audit_runs_website_created_idx "
                "ON audit_runs (website_id, created_at DESC)"
            )
        )
        await conn.execute(text("DROP INDEX IF EXISTS audit_runs_status_idx"))
        await conn.execute(
            text(
                "CREATE INDEX audit_runs_status_idx "
                "ON audit_runs (status) WHERE deleted_at IS NULL"
            )
        )


@pytest_asyncio.fixture()
async def db_engine(settings: Settings) -> AsyncEngine:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable for repository tests: {exc}")

    await _prepare_database(engine)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
