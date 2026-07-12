"""API tests for report share link create + resolve."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.share_report import SHARE_TOKEN_SALT
from app.core.config import Settings, clear_settings_cache
from app.core.signed_tokens import sign_payload
from app.dependencies.db import get_db_session
from app.domain.audit_status import AuditStatus
from app.main import create_app
from app.models.audit_finding import AuditFinding
from app.models.audit_run import AuditRun
from app.models.health_score import HealthScore
from app.models.recommendation import RecommendationRow
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate


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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    clear_settings_cache()


async def _seed(session: AsyncSession, *, status: str = AuditStatus.COMPLETE.value) -> AuditRun:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="API Share Org", slug=f"api-share-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="API Share Project",
            slug=f"api-share-p-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://api-share.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://api-share.example/",
        canonical_url="https://api-share.example/",
        status=status,
        progress_percent=100 if status.startswith("complete") else 10,
        started_at=now,
        completed_at=now if status.startswith("complete") else None,
        duration_ms=1000 if status.startswith("complete") else None,
        health_score=90 if status.startswith("complete") else None,
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()
    if status.startswith("complete"):
        session.add(
            HealthScore(
                audit_run_id=audit.id,
                overall_score=90,
                seo_score=90,
                accessibility_score=90,
                security_score=90,
                performance_score=90,
                business_score=90,
                grade="A-",
                confidence=95,
                category_scores={
                    "seo": 90,
                    "accessibility": 90,
                    "security": 90,
                    "performance": 90,
                    "business": 90,
                },
                breakdown={},
                penalties={"items": []},
                configuration_version="scoring_config@test",
            )
        )
        session.add(
            AuditFinding(
                audit_run_id=audit.id,
                engine_name="seo",
                finding_id="seo.viewport.missing",
                category="seo",
                severity="high",
                status="fail",
                issue="Missing viewport",
                technical_detail="No viewport meta",
                evidence={},
                confidence=100,
            )
        )
        session.add(
            RecommendationRow(
                audit_run_id=audit.id,
                recommendation_id="rec.seo.add_viewport",
                title="Add viewport",
                recommendation_text="Add viewport meta tag.",
                category="SEO",
                priority="High",
                estimated_effort="Very Low",
                estimated_impact="High",
                priority_score=70,
                confidence=90,
                is_quick_win=True,
                affected_findings=["seo.viewport.missing"],
                related_rules=["seo.viewport"],
                prompt_version="recommendation_rules@test",
                model_used="rules:v1",
                provider="rules",
                version=1,
                is_fallback=False,
            )
        )
    await session.commit()
    return audit


def _error_code(payload: dict) -> str:
    if "error" in payload and isinstance(payload["error"], dict):
        return str(payload["error"].get("code") or "")
    detail = payload.get("detail")
    if isinstance(detail, dict):
        return str(detail.get("code") or "")
    return ""


@pytest.mark.asyncio
async def test_create_share_link_and_fetch_report(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    audit = await _seed(db_session)

    create = await api_client.post(f"/api/v1/audits/{audit.id}/share")
    assert create.status_code == 201, create.text
    body = create.json()
    assert "share_url" in body
    assert "expires_at" in body
    assert body["audit_id"] == str(audit.id)
    assert "/share/" in body["share_url"]
    token = body["token"]

    fetched = await api_client.get(f"/api/v1/share/{token}")
    assert fetched.status_code == 200, fetched.text
    report = fetched.json()
    assert report["audit_id"] == str(audit.id)
    assert report["schema_version"] == "report.v1"
    assert report["overview"]["overall_score"] == 90


@pytest.mark.asyncio
async def test_invalid_token_returns_404(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/share/not-a-valid-token")
    assert resp.status_code == 404
    assert _error_code(resp.json()) == "SHARE_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_tampered_token_returns_404(
    api_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    audit = await _seed(db_session)
    token, _ = sign_payload(
        {"aid": str(audit.id)},
        secret=settings.secret_key,
        salt=SHARE_TOKEN_SALT,
        ttl_seconds=3600,
    )
    body, _, sig = token.partition(".")
    tampered = f"{body}x.{sig}"
    resp = await api_client.get(f"/api/v1/share/{tampered}")
    assert resp.status_code == 404
    assert _error_code(resp.json()) == "SHARE_TOKEN_INVALID"


@pytest.mark.asyncio
async def test_expired_token_returns_410(
    api_client: AsyncClient,
    db_session: AsyncSession,
    settings: Settings,
) -> None:
    audit = await _seed(db_session)

    import base64
    import hashlib
    import hmac
    import json
    import time

    past = int(time.time()) - 30
    payload = json.dumps(
        {"aid": str(audit.id), "exp": past},
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    body_b64 = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    digest = hmac.new(
        f"{SHARE_TOKEN_SALT}:{settings.secret_key}".encode(),
        body_b64.encode(),
        hashlib.sha256,
    ).digest()
    sig = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    resp = await api_client.get(f"/api/v1/share/{body_b64}.{sig}")
    assert resp.status_code == 410
    assert _error_code(resp.json()) == "SHARE_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_share_incomplete_audit_conflict(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    audit = await _seed(db_session, status=AuditStatus.ANALYZING.value)
    resp = await api_client.post(f"/api/v1/audits/{audit.id}/share")
    assert resp.status_code in (404, 409)
