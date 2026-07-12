"""Application use-case tests for report export."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.export import (
    ExportCsvUseCase,
    ExportFailedError,
    ExportJsonUseCase,
    ExportPdfUseCase,
)
from app.domain.audit_status import AuditStatus
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
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError


@pytest_asyncio.fixture()
async def session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        try:
            yield sess
            await sess.commit()
        except Exception:
            await sess.rollback()
            raise


async def _seed(session: AsyncSession, *, status: str = AuditStatus.COMPLETE.value) -> AuditRun:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="Export UC Org", slug=f"exp-uc-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="Export UC Project",
            slug=f"exp-uc-p-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://export-uc.example")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://export-uc.example/",
        canonical_url="https://export-uc.example/",
        status=status,
        progress_percent=100 if status.startswith("complete") else 10,
        started_at=now,
        completed_at=now if status.startswith("complete") else None,
        duration_ms=1000 if status.startswith("complete") else None,
        health_score=88 if status.startswith("complete") else None,
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()
    if status.startswith("complete"):
        session.add(
            HealthScore(
                audit_run_id=audit.id,
                overall_score=88,
                seo_score=88,
                accessibility_score=88,
                security_score=88,
                performance_score=88,
                business_score=88,
                grade="B+",
                confidence=90,
                category_scores={
                    "seo": 88,
                    "accessibility": 88,
                    "security": 88,
                    "performance": 88,
                    "business": 88,
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
                finding_id="seo.title.missing",
                category="seo",
                severity="medium",
                status="fail",
                issue="Missing title",
                technical_detail="No title tag",
                evidence={},
                confidence=90,
            )
        )
        session.add(
            RecommendationRow(
                audit_run_id=audit.id,
                recommendation_id="rec.seo.add_title",
                title="Add title tag",
                recommendation_text="Provide a descriptive title.",
                category="SEO",
                priority="Medium",
                estimated_effort="Low",
                estimated_impact="Medium",
                priority_score=50,
                confidence=90,
                is_quick_win=True,
                affected_findings=["seo.title.missing"],
                related_rules=["seo.title"],
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
async def test_export_pdf_use_case(session: AsyncSession) -> None:
    audit = await _seed(session)
    result = await ExportPdfUseCase(session).execute(audit.id)
    assert result.artifact.filename == "audit-report.pdf"
    assert result.artifact.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_export_json_use_case(session: AsyncSession) -> None:
    audit = await _seed(session)
    result = await ExportJsonUseCase(session).execute(audit.id)
    assert result.artifact.filename == "audit-report.json"
    assert b"schema_version" in result.artifact.content


@pytest.mark.asyncio
async def test_export_csv_use_case(session: AsyncSession) -> None:
    audit = await _seed(session)
    result = await ExportCsvUseCase(session).execute(audit.id)
    assert result.artifact.filename == "audit-report.csv"
    text = result.artifact.content.decode("utf-8-sig")
    assert "Findings" in text
    assert "Recommendations" in text


@pytest.mark.asyncio
async def test_export_not_found(session: AsyncSession) -> None:
    with pytest.raises(AuditNotFoundError):
        await ExportPdfUseCase(session).execute(uuid4())


@pytest.mark.asyncio
async def test_export_not_ready(session: AsyncSession) -> None:
    audit = await _seed(session, status=AuditStatus.CRAWLING.value)
    with pytest.raises(ReportNotReadyError):
        await ExportJsonUseCase(session).execute(audit.id)


@pytest.mark.asyncio
async def test_export_failed_maps_renderer_errors(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit = await _seed(session)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.export.pdf_exporter.PdfReportExporter.export",
        boom,
    )
    with pytest.raises(ExportFailedError) as exc_info:
        await ExportPdfUseCase(session).execute(audit.id)
    assert exc_info.value.code == "EXPORT_FAILED"
