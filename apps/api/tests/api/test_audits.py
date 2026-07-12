"""Audit API endpoint tests — Sprint 14 enriched GET + sync pipeline POST."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.v1 import audits as audits_api
from app.core.config import Settings, clear_settings_cache
from app.dependencies.db import get_db_session
from app.domain.audit_status import AuditStatus
from app.main import create_app
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate
from tests.helpers.pipeline_fixtures import build_stub_pipeline, mock_http_client


@pytest_asyncio.fixture()
async def api_client(db_engine: AsyncEngine, settings: Settings) -> AsyncIterator[AsyncClient]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app(settings)
    await app.state.engine.dispose()
    app.state.engine = db_engine
    app.state.session_factory = factory
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[audits_api.get_pipeline_factory] = lambda: (
        lambda **kwargs: build_stub_pipeline()
    )
    app.dependency_overrides[audits_api.get_pipeline_kwargs] = lambda: {}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    clear_settings_cache()


async def _seed_website(session: AsyncSession):
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="API Org", slug=f"api-org-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="API Project",
            slug=f"api-project-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://api-example.com")
    )
    await session.commit()
    return website


async def _wait_for_terminal(
    client: AsyncClient,
    audit_id: str,
    *,
    timeout_s: float = 30.0,
) -> dict:
    import time

    deadline = time.monotonic() + timeout_s
    last: dict = {}
    while time.monotonic() < deadline:
        get_resp = await client.get(f"/api/v1/audits/{audit_id}")
        assert get_resp.status_code == 200
        last = get_resp.json()
        if last["status"] in {
            AuditStatus.COMPLETE.value,
            AuditStatus.COMPLETE_WITH_WARNINGS.value,
            AuditStatus.FAILED.value,
            AuditStatus.CANCELLED.value,
        }:
            return last
        await asyncio.sleep(0.05)
    raise AssertionError(f"audit {audit_id} did not reach terminal status: {last}")


@pytest.mark.asyncio
async def test_post_and_get_audit(api_client: AsyncClient, db_session: AsyncSession) -> None:
    website = await _seed_website(db_session)

    create_resp = await api_client.post("/api/v1/audits", json={"website_id": str(website.id)})
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["status"] == AuditStatus.PENDING.value
    assert "created" in body["message"].lower()
    audit_id = body["audit_id"]

    detail = await _wait_for_terminal(api_client, audit_id)
    assert detail["audit_id"] == audit_id
    assert detail["website_id"] == str(website.id)
    assert detail["status"] in {
        AuditStatus.COMPLETE.value,
        AuditStatus.COMPLETE_WITH_WARNINGS.value,
    }
    assert detail["progress"] == 100
    assert detail["current_engine"] is None
    assert isinstance(detail["engine_summary"], list)
    assert len(detail["engine_summary"]) == 10
    assert "finding_counts" in detail
    assert detail["finding_counts"]["total"] == 0
    # Stub pipeline may omit recommendation_analysis persistence payload
    assert "scores" in detail
    assert "ai_summary" not in detail
    # recommendations key may be null when stubs skip analysis write
    assert "recommendations" in detail


@pytest.mark.asyncio
async def test_get_audit_payload_with_live_engines(
    db_engine: AsyncEngine,
    settings: Settings,
    db_session: AsyncSession,
) -> None:
    website = await _seed_website(db_session)
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    http = mock_http_client()

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app(settings)
    await app.state.engine.dispose()
    app.state.engine = db_engine
    app.state.session_factory = factory
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[audits_api.get_pipeline_factory] = lambda: None
    app.dependency_overrides[audits_api.get_pipeline_kwargs] = lambda: {
        "resolve_dns": True,
        "dns_lookup": lambda hostname, timeout=5.0: ["93.184.216.34"],
        "crawler_http_client": http,
    }

    transport = ASGITransport(app=app)
    async with http:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/api/v1/audits",
                json={"website_id": str(website.id)},
            )
            assert create_resp.status_code == 201
            audit_id = create_resp.json()["audit_id"]
            assert create_resp.json()["status"] == AuditStatus.PENDING.value

            detail = await _wait_for_terminal(client, audit_id)
            assert detail["status"] in {
                AuditStatus.COMPLETE.value,
                AuditStatus.COMPLETE_WITH_WARNINGS.value,
            }
            assert detail["health_score"] is not None
            assert detail["health_score"]["overall_score"] is not None
            assert detail["health_score"]["grade"]
            assert detail["category_scores"] is not None
            assert detail["scores"]["overall"] == detail["health_score"]["overall_score"]
            assert len(detail["engine_summary"]) == 10
            assert detail["engine_summary"][0]["engine_name"] == "url_validation"
            assert detail["engine_summary"][0]["status"] == "success"
            assert detail["engine_summary"][-1]["engine_name"] == "recommendation"
            assert detail["finding_counts"]["total"] >= 0
            assert detail["recommendations"] is not None
            assert "priority_summary" in detail["recommendations"]
            assert "quick_wins" in detail["recommendations"]
            assert "counts" in detail["recommendations"]
            assert "ai_summary" not in detail
            assert "executive_summary" not in detail

    app.dependency_overrides.clear()
    clear_settings_cache()


@pytest.mark.asyncio
async def test_post_audit_invalid_website(api_client: AsyncClient) -> None:
    resp = await api_client.post("/api/v1/audits", json={"website_id": str(uuid4())})
    assert resp.status_code == 404
    error = resp.json()["error"]
    assert error["code"] == "WEBSITE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_audit_not_found(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/audits/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AUDIT_NOT_FOUND"
