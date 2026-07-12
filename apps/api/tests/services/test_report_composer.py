"""Report Composer DB integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.get_report import GetAuditReportUseCase
from app.domain.audit_status import AuditStatus
from app.models.audit_finding import AuditFinding
from app.models.audit_run import AuditRun
from app.models.engine_execution import EngineExecution
from app.models.health_score import HealthScore
from app.models.recommendation import RecommendationRow
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.report import ReportRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate
from app.services.report.composer import ReportComposer
from app.services.report.constants import SCHEMA_VERSION
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError


async def _seed_completed_audit(session: AsyncSession, *, with_data: bool = True) -> AuditRun:
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name="Report Org", slug=f"report-org-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name="Report Project",
            slug=f"report-proj-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://example.com")
    )
    now = datetime.now(UTC)
    audit = AuditRun(
        website_id=website.id,
        organization_id=org.id,
        project_id=project.id,
        requested_url="https://example.com/",
        canonical_url="https://example.com/",
        status=AuditStatus.COMPLETE.value,
        progress_percent=100,
        started_at=now,
        completed_at=now,
        duration_ms=4200,
        health_score=81,
        seo_score=80,
        accessibility_score=85,
        security_score=70,
        performance_score=75,
        business_score=78,
        confidence_score=90,
        scoring_config_version="scoring_config@test",
        engine_versions={},
        pipeline_metadata={},
    )
    session.add(audit)
    await session.flush()

    if with_data:
        session.add(
            HealthScore(
                audit_run_id=audit.id,
                overall_score=81,
                seo_score=80,
                accessibility_score=85,
                security_score=70,
                performance_score=75,
                business_score=78,
                grade="B-",
                confidence=90,
                category_scores={
                    "seo": 80,
                    "accessibility": 85,
                    "security": 70,
                    "performance": 75,
                    "business": 78,
                },
                breakdown={"overall": {"score": 81}},
                penalties={"items": []},
                configuration_version="scoring_config@test",
            )
        )
        session.add_all(
            [
                AuditFinding(
                    audit_run_id=audit.id,
                    engine_name="seo",
                    finding_id="seo.title.missing",
                    category="seo",
                    severity="high",
                    status="fail",
                    issue="Missing title",
                    technical_detail="No title tag",
                    evidence={"location": "head"},
                    confidence=100,
                ),
                AuditFinding(
                    audit_run_id=audit.id,
                    engine_name="security",
                    finding_id="sec.https.non_https_url",
                    category="security",
                    severity="critical",
                    status="fail",
                    issue="Non-HTTPS URL",
                    technical_detail="Page served over HTTP",
                    evidence={},
                    confidence=100,
                ),
                AuditFinding(
                    audit_run_id=audit.id,
                    engine_name="business",
                    finding_id="biz.seo.missing_title_visibility",
                    category="business",
                    severity="high",
                    status="fail",
                    issue="Search visibility impacted",
                    technical_detail="Mapped from missing title",
                    evidence={"impact": "Lower CTR potential"},
                    confidence=100,
                ),
                AuditFinding(
                    audit_run_id=audit.id,
                    engine_name="accessibility",
                    finding_id="a11y.buttons.empty",
                    category="accessibility",
                    severity="medium",
                    status="fail",
                    issue="Empty button",
                    technical_detail="Button has no name",
                    evidence={},
                    confidence=100,
                ),
            ]
        )
        session.add_all(
            [
                RecommendationRow(
                    audit_run_id=audit.id,
                    recommendation_id="rec.seo.add_document_title",
                    finding_id="seo.title.missing",
                    title="Add a descriptive document title",
                    recommendation_text="Set a unique title.",
                    technical_reason="Title missing",
                    business_explanation="Improves CTR potential",
                    category="SEO",
                    priority="High",
                    estimated_effort="Very Low",
                    estimated_impact="High",
                    priority_score=72.0,
                    confidence=95,
                    is_quick_win=True,
                    affected_findings=["seo.title.missing", "biz.seo.missing_title_visibility"],
                    related_rules=["seo.title"],
                    prompt_version="recommendation_rules@test",
                    model_used="rules:v1",
                    provider="rules",
                    version=1,
                    is_fallback=False,
                ),
                RecommendationRow(
                    audit_run_id=audit.id,
                    recommendation_id="rec.sec.add_csp",
                    finding_id="sec.headers.missing_csp",
                    title="Deploy CSP",
                    recommendation_text="Add Content-Security-Policy.",
                    technical_reason="CSP missing",
                    business_explanation="Reduces XSS risk",
                    category="Security",
                    priority="High",
                    estimated_effort="High",
                    estimated_impact="High",
                    priority_score=80.0,
                    confidence=90,
                    is_quick_win=False,
                    affected_findings=["sec.headers.missing_csp"],
                    related_rules=["sec.headers.csp"],
                    prompt_version="recommendation_rules@test",
                    model_used="rules:v1",
                    provider="rules",
                    version=1,
                    is_fallback=False,
                ),
            ]
        )
        session.add(
            EngineExecution(
                audit_run_id=audit.id,
                engine_name="seo",
                engine_version="0.1.0",
                attempt=1,
                status="success",
                started_at=now,
                completed_at=now,
                execution_time_ms=12,
                configuration={},
            )
        )
        session.add(
            EngineExecution(
                audit_run_id=audit.id,
                engine_name="health",
                engine_version="0.1.0",
                attempt=1,
                status="success",
                started_at=now,
                completed_at=now,
                execution_time_ms=5,
                configuration={},
            )
        )
    await session.flush()
    return audit


@pytest.mark.asyncio
async def test_successful_report_composition(db_session: AsyncSession) -> None:
    audit = await _seed_completed_audit(db_session)
    dto = await ReportComposer(db_session).compose(audit.id)

    assert dto.audit_id == audit.id
    assert dto.schema_version == SCHEMA_VERSION
    assert dto.report_version == 1
    assert dto.report_hash is not None
    assert len(dto.report_hash) == 64
    assert dto.overview.overall_score == 81
    assert dto.overview.overall_grade == "B-"
    assert dto.health.grade == "B-"
    assert list(dto.health.category_scores.keys()) == [
        "seo",
        "accessibility",
        "security",
        "performance",
        "business",
    ]
    assert dto.statistics.total_findings == 4
    assert dto.statistics.finding_count == 4
    assert dto.statistics.critical_count == 1
    assert dto.statistics.recommendation_count == 2
    assert dto.statistics.pipeline_duration == 4200
    assert len(dto.critical_issues) == 1
    assert dto.critical_issues[0].id == "sec.https.non_https_url"
    assert len(dto.quick_wins) == 1
    assert dto.quick_wins[0].recommendation_id == "rec.seo.add_document_title"
    assert dto.seo.findings[0].id == "seo.title.missing"
    assert dto.seo.findings[0].rule_id == "seo.title"
    assert dto.seo.findings[0].location == "head"
    assert len(dto.business_impacts) >= 1
    assert len(dto.engine_summary) == 2
    assert dto.report_id is not None
    assert "4 findings detected." in dto.summary

    saved = await ReportRepository(db_session).get_by_audit(audit.id)
    assert saved is not None
    assert saved.schema_version == SCHEMA_VERSION
    assert saved.version == 1
    assert saved.report_hash == dto.report_hash
    assert saved.executive_summary == dto.summary


@pytest.mark.asyncio
async def test_cached_report_returned(db_session: AsyncSession) -> None:
    audit = await _seed_completed_audit(db_session)
    first = await ReportComposer(db_session).compose(audit.id)
    second = await ReportComposer(db_session).compose(audit.id)
    assert first.report_id == second.report_id
    assert second.report_version == 1
    assert second.metadata.report_version == 1
    assert second.report_hash == first.report_hash


@pytest.mark.asyncio
async def test_report_regeneration_unchanged_content_keeps_version(
    db_session: AsyncSession,
) -> None:
    audit = await _seed_completed_audit(db_session)
    first = await ReportComposer(db_session).compose(audit.id)
    regenerated = await ReportComposer(db_session).regenerate(audit.id)
    assert regenerated.report_id == first.report_id
    assert regenerated.report_version == 1
    assert regenerated.metadata.report_version == 1
    assert regenerated.report_hash == first.report_hash
    saved = await ReportRepository(db_session).get_by_audit(audit.id)
    assert saved is not None
    assert saved.version == 1
    assert saved.report_hash == first.report_hash


@pytest.mark.asyncio
async def test_report_regeneration_bumps_version_when_content_changes(
    db_session: AsyncSession,
) -> None:
    audit = await _seed_completed_audit(db_session)
    first = await ReportComposer(db_session).compose(audit.id)
    assert first.report_version == 1

    # Mutate persisted findings so the composed projection changes.
    db_session.add(
        AuditFinding(
            audit_run_id=audit.id,
            engine_name="performance",
            finding_id="perf.lcp.slow",
            category="performance",
            severity="high",
            status="fail",
            issue="Slow LCP",
            technical_detail="LCP above threshold",
            evidence={},
            confidence=100,
        )
    )
    await db_session.flush()

    regenerated = await ReportComposer(db_session).regenerate(audit.id)
    assert regenerated.report_version == 2
    assert regenerated.metadata.report_version == 2
    assert regenerated.report_hash != first.report_hash
    assert regenerated.statistics.finding_count == 5
    saved = await ReportRepository(db_session).get_by_audit(audit.id)
    assert saved is not None
    assert saved.version == 2
    assert saved.report_hash == regenerated.report_hash


@pytest.mark.asyncio
async def test_not_ready_and_not_found(db_session: AsyncSession) -> None:
    audit = await _seed_completed_audit(db_session, with_data=False)
    audit.status = AuditStatus.PENDING.value
    await db_session.flush()

    with pytest.raises(ReportNotReadyError):
        await ReportComposer(db_session).compose(audit.id)

    with pytest.raises(AuditNotFoundError):
        await ReportComposer(db_session).compose(uuid4())


@pytest.mark.asyncio
async def test_use_case_wrapper(db_session: AsyncSession) -> None:
    audit = await _seed_completed_audit(db_session)
    result = await GetAuditReportUseCase(db_session).execute(audit.id)
    assert result.report.statistics.total_findings == 4
    assert result.report.report_version == 1
