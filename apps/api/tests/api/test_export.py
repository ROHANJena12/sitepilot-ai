"""API tests for report export download endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, clear_settings_cache
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
        OrganizationCreate(name="API Export Org", slug=f"api-exp-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="API Export Project",
            slug=f"api-exp-p-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://api-export.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://api-export.example/",
        canonical_url="https://api-export.example/",
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


@pytest.mark.asyncio
async def test_export_pdf_endpoint(api_client: AsyncClient, db_session: AsyncSession) -> None:
    audit = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert 'attachment; filename="audit-report.pdf"' in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_export_json_endpoint(api_client: AsyncClient, db_session: AsyncSession) -> None:
    audit = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/export/json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    assert 'attachment; filename="audit-report.json"' in resp.headers["content-disposition"]
    body = resp.json()
    assert body["audit_id"] == str(audit.id)
    assert body["schema_version"] == "report.v1"


@pytest.mark.asyncio
async def test_export_csv_endpoint(api_client: AsyncClient, db_session: AsyncSession) -> None:
    audit = await _seed(db_session)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert 'attachment; filename="audit-report.csv"' in resp.headers["content-disposition"]
    text = resp.content.decode("utf-8-sig")
    assert "Findings" in text
    assert "Recommendations" in text


@pytest.mark.asyncio
async def test_export_404(api_client: AsyncClient) -> None:
    resp = await api_client.get(f"/api/v1/audits/{uuid4()}/export/json")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "AUDIT_NOT_FOUND"


@pytest.mark.asyncio
async def test_export_409(api_client: AsyncClient, db_session: AsyncSession) -> None:
    audit = await _seed(db_session, status=AuditStatus.ANALYZING.value)
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/export/pdf")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "REPORT_NOT_READY"


@pytest.mark.asyncio
async def test_export_503(
    api_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit = await _seed(db_session)

    def boom(_self: object, _report: object) -> None:
        raise RuntimeError("renderer down")

    monkeypatch.setattr(
        "app.export.pdf_exporter.PdfReportExporter.export",
        boom,
    )
    resp = await api_client.get(f"/api/v1/audits/{audit.id}/export/pdf")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "EXPORT_FAILED"
