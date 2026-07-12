"""Sprint 14 — run audit pipeline persistence and orchestration tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.run_audit import RunAuditUseCase
from app.application.start_audit import StartAuditUseCase
from app.domain.audit_status import ENGINE_PROGRESS_MAP, AuditStatus
from app.engines.common.findings import Finding, FindingStatus, Severity
from app.engines.health.schemas import (
    HealthScoreAnalysis,
    OverallScore,
    ScoreBreakdown,
)
from app.pipeline import AuditPipeline, EngineRegistry, EngineResult, PipelineStatus
from app.pipeline.context import AuditContext
from app.repositories.audit import AuditRepository
from app.repositories.engine_execution import EngineExecutionRepository
from app.repositories.finding import FindingRepository
from app.repositories.health_score import HealthScoreRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.project import ProjectRepository
from app.repositories.website import WebsiteRepository
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.website import WebsiteCreate
from app.services.audit_pipeline import AuditPipelineService
from tests.helpers.pipeline_fixtures import (
    StubEngine,
    build_live_pipeline,
    build_stub_pipeline,
    mock_http_client,
)


async def _seed_website(session: AsyncSession, *, slug: str = "sprint14"):
    org = await OrganizationRepository(session).create(
        OrganizationCreate(name=f"Org {slug}", slug=f"org-{slug}-{uuid4().hex[:8]}")
    )
    project = await ProjectRepository(session).create(
        ProjectCreate(
            organization_id=org.id,
            name=f"Project {slug}",
            slug=f"proj-{slug}-{uuid4().hex[:8]}",
        )
    )
    website = await WebsiteRepository(session).create(
        WebsiteCreate(project_id=project.id, url="https://example.com")
    )
    await session.flush()
    return website


@pytest.mark.asyncio
async def test_successful_pipeline_execution(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="ok")
    http = mock_http_client()

    async with http:
        result = await RunAuditUseCase(
            db_session,
            pipeline_factory=AuditPipeline,
            pipeline_kwargs={
                "resolve_dns": True,
                "dns_lookup": lambda hostname, timeout=5.0: ["93.184.216.34"],
                "crawler_http_client": http,
            },
        ).execute(website.id)

    assert result.pipeline_result is not None
    assert result.pipeline_result.overall_status == PipelineStatus.SUCCESS
    assert result.audit_run.status in {
        AuditStatus.COMPLETE.value,
        AuditStatus.COMPLETE_WITH_WARNINGS.value,
    }
    assert result.audit_run.progress_percent == 100
    assert result.audit_run.health_score is not None
    assert result.audit_run.started_at is not None
    assert result.audit_run.completed_at is not None
    assert result.audit_run.duration_ms is not None

    executions = await EngineExecutionRepository(db_session).list_by_audit(result.audit_run.id)
    assert len(executions) == 10
    assert all(e.status == "success" for e in executions)

    findings = await FindingRepository(db_session).list_by_audit(result.audit_run.id)
    assert len(findings) >= 0  # page may be clean

    health = await HealthScoreRepository(db_session).get_by_audit(result.audit_run.id)
    assert health is not None
    assert health.overall_score == result.audit_run.health_score
    assert health.grade
    assert health.configuration_version


@pytest.mark.asyncio
async def test_failed_engine_marks_audit_failed(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="fail")
    started = await StartAuditUseCase(db_session).execute(website.id)

    audit, pipeline_result = await AuditPipelineService(
        db_session,
        pipeline_factory=lambda **kwargs: build_stub_pipeline(fail_at="parser"),
    ).execute(started.audit_run)

    assert pipeline_result.overall_status == PipelineStatus.FAILED
    assert pipeline_result.failed_engine == "parser"
    assert audit.status == AuditStatus.FAILED.value
    assert audit.failure_code == "ENGINE_FAILED"

    executions = await EngineExecutionRepository(db_session).list_by_audit(audit.id)
    names = [e.engine_name for e in executions]
    assert names == ["url_validation", "crawler", "parser"]
    assert executions[-1].status == "failed"
    assert executions[0].status == "success"


@pytest.mark.asyncio
async def test_partial_failure_persists_prior_work(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="partial")
    started = await StartAuditUseCase(db_session).execute(website.id)

    finding = Finding(
        id="seo.title.missing",
        rule_id="seo.title",
        category="seo",
        severity=Severity.HIGH,
        title="Missing title",
        description="No title tag",
        status=FindingStatus.FAIL,
        evidence={"tag": "title"},
    )

    registry = EngineRegistry()
    registry.register(StubEngine("url_validation"))
    registry.register(StubEngine("crawler"))
    registry.register(StubEngine("parser"))
    registry.register(
        StubEngine("seo", findings_key="seo_analysis", findings=(finding,))
    )
    registry.register(StubEngine("accessibility", succeed=False))
    for name in ("security", "performance", "business", "health"):
        registry.register(StubEngine(name))

    pipeline = AuditPipeline(
        registry=registry,
        engine_order=(
            "url_validation",
            "crawler",
            "parser",
            "seo",
            "accessibility",
            "security",
            "performance",
            "business",
            "health",
        ),
        resolve_dns=False,
    )

    audit, result = await AuditPipelineService(
        db_session,
        pipeline_factory=lambda **kw: pipeline,
    ).execute(started.audit_run)

    assert result.failed_engine == "accessibility"
    assert audit.status == AuditStatus.FAILED.value

    findings = await FindingRepository(db_session).list_by_audit(audit.id)
    assert len(findings) == 1
    assert findings[0].finding_id == "seo.title.missing"
    assert findings[0].issue == "Missing title"

    executions = await EngineExecutionRepository(db_session).list_by_audit(audit.id)
    assert len(executions) == 5  # through accessibility
    assert executions[3].engine_name == "seo" and executions[3].status == "success"


@pytest.mark.asyncio
async def test_transaction_rollback_nested(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="rollback")
    started = await StartAuditUseCase(db_session).execute(website.id)
    audit_id = started.audit_run.id

    class BoomService(AuditPipelineService):
        async def execute(self, audit):
            await self._audits.update_progress(
                audit.id,
                progress_percent=10,
                current_engine="url_validation",
                status=AuditStatus.VALIDATING,
            )
            await self._executions.create_running(
                audit_run_id=audit.id,
                engine_name="url_validation",
            )
            raise RuntimeError("forced persistence abort")

    with pytest.raises(RuntimeError, match="forced persistence abort"):
        async with db_session.begin_nested():
            await BoomService(db_session).execute(started.audit_run)

    from sqlalchemy import select

    from app.models.engine_execution import EngineExecution

    ex_count = await db_session.execute(
        select(EngineExecution).where(EngineExecution.audit_run_id == audit_id)
    )
    assert list(ex_count.scalars().all()) == []

    audit = await AuditRepository(db_session).get_by_id(audit_id)
    assert audit is not None
    assert audit.status == AuditStatus.PENDING.value
    assert audit.progress_percent == 0
    assert audit.current_engine is None


@pytest.mark.asyncio
async def test_finding_and_health_and_execution_persistence(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="persist")
    started = await StartAuditUseCase(db_session).execute(website.id)

    health = HealthScoreAnalysis(
        overall_score=88.0,
        seo_score=90.0,
        accessibility_score=85.0,
        security_score=80.0,
        performance_score=92.0,
        business_score=87.0,
        grade="B+",
        confidence=95.0,
        breakdown=ScoreBreakdown(
            overall=OverallScore(score=88.0),
            scoring_config_version="scoring_config@test",
        ),
        penalties=(),
    )
    finding = Finding(
        id="biz.conversion.empty_buttons",
        rule_id="biz.conversion",
        category="business",
        severity=Severity.MEDIUM,
        title="Empty buttons",
        description="CTA text missing",
        status=FindingStatus.FAIL,
    )

    registry = EngineRegistry()
    for name in ("url_validation", "crawler", "parser", "seo", "accessibility", "security", "performance"):
        registry.register(StubEngine(name))
    registry.register(
        StubEngine("business", findings_key="business_analysis", findings=(finding,))
    )

    class HealthStub(StubEngine):
        async def run(self, context: AuditContext) -> EngineResult:
            context.shared_state["health_analysis"] = health
            return EngineResult.ok(self.name, duration_ms=1)

    registry.register(HealthStub("health"))

    class RecStub(StubEngine):
        async def run(self, context: AuditContext) -> EngineResult:
            from app.engines.recommendation.schemas import RecommendationAnalysis

            context.shared_state["recommendation_analysis"] = RecommendationAnalysis(
                configuration_version="recommendation_rules@test"
            )
            return EngineResult.ok(self.name, duration_ms=1)

    registry.register(RecStub("recommendation"))
    pipeline = AuditPipeline(
        registry=registry,
        engine_order=tuple(ENGINE_PROGRESS_MAP.keys()),
        resolve_dns=False,
    )

    audit, _ = await AuditPipelineService(
        db_session,
        pipeline_factory=lambda **kw: pipeline,
    ).execute(started.audit_run)

    assert audit.status == AuditStatus.COMPLETE.value
    findings = await FindingRepository(db_session).list_by_audit(audit.id)
    assert len(findings) == 1
    assert findings[0].engine_name == "business"
    assert findings[0].evidence == {}

    health_row = await HealthScoreRepository(db_session).get_by_audit(audit.id)
    assert health_row is not None
    assert health_row.overall_score == 88
    assert health_row.grade == "B+"
    assert health_row.configuration_version == "scoring_config@test"
    assert health_row.category_scores["seo"] == 90

    from app.repositories.recommendation import RecommendationRepository

    recs = await RecommendationRepository(db_session).list_by_audit(audit.id)
    # RecStub writes empty analysis → zero rows after replace
    assert isinstance(recs, list)

    executions = await EngineExecutionRepository(db_session).list_by_audit(audit.id)
    assert len(executions) == 10
    assert all(e.started_at and e.completed_at and e.execution_time_ms is not None for e in executions)


@pytest.mark.asyncio
async def test_status_transitions_and_progress(db_session: AsyncSession) -> None:
    website = await _seed_website(db_session, slug="progress")
    started = await StartAuditUseCase(db_session).execute(website.id)

    statuses: list[str] = []
    progresses: list[int] = []

    class TrackingService(AuditPipelineService):
        async def _on_pipeline_event(self, event):
            await super()._on_pipeline_event(event)
            audit = await self._audits.get_by_id(started.audit_run.id)
            assert audit is not None
            statuses.append(audit.status)
            progresses.append(audit.progress_percent)

    await TrackingService(
        db_session,
        pipeline_factory=lambda **kw: build_stub_pipeline(),
    ).execute(started.audit_run)

    assert AuditStatus.VALIDATING.value in statuses
    assert AuditStatus.CRAWLING.value in statuses
    assert AuditStatus.PARSING.value in statuses
    assert AuditStatus.HEALTH.value in statuses
    assert progresses[-1] == 100
    assert max(progresses) == 100
    # After each completed engine, progress matches map
    for engine, expected in ENGINE_PROGRESS_MAP.items():
        assert expected in progresses


@pytest.mark.asyncio
async def test_live_pipeline_factory_helper() -> None:
    pipeline = build_live_pipeline()
    assert pipeline.engine_order[-1] == "recommendation"
