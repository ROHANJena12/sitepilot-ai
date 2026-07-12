"""Audit Run HTTP endpoints — Sprint 14 pipeline execution + enriched GET."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_background import schedule_audit_pipeline
from app.application.get_report import GetAuditReportUseCase
from app.application.run_audit import RunAuditUseCase
from app.application.start_audit import StartAuditUseCase
from app.dependencies.db import DbSession
from app.domain.exceptions import DomainValidationError
from app.models.audit_run import AuditRun
from app.pipeline import AuditPipeline
from app.repositories.audit import AuditRepository
from app.repositories.engine_execution import EngineExecutionRepository
from app.repositories.finding import FindingRepository
from app.repositories.health_score import HealthScoreRepository
from app.repositories.recommendation import RecommendationRepository
from app.schemas.audit import AuditCreateRequest, AuditCreateResponse, AuditScoresResponse
from app.schemas.report import (
    AuditReportResponse,
    EngineSummaryItem,
    FindingCountsResponse,
    HealthScoreResponse,
    PrioritySummaryResponse,
    RecommendationItemResponse,
    RecommendationSummaryResponse,
)
from app.services.audit_pipeline import PipelineFactory
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError
from app.services.report.schemas import AuditReportDTO

# Effort / impact constants for summary buckets (mirror engine constants).
_HIGH_IMPACT = frozenset({"Critical", "High"})
_LONG_TERM = frozenset({"High", "Very High"})

router = APIRouter(prefix="/audits", tags=["audits"])


def get_pipeline_factory() -> PipelineFactory | None:
    """Override in tests to inject stub engines / mock HTTP."""
    return None


def get_pipeline_kwargs() -> dict[str, Any]:
    """Override in tests (e.g. resolve_dns=False, crawler_http_client=...)."""
    return {}


def get_run_audit_use_case(
    session: DbSession,
    pipeline_factory: Annotated[PipelineFactory | None, Depends(get_pipeline_factory)],
    pipeline_kwargs: Annotated[dict[str, Any], Depends(get_pipeline_kwargs)],
) -> RunAuditUseCase:
    return RunAuditUseCase(
        session,
        pipeline_factory=pipeline_factory or AuditPipeline,
        pipeline_kwargs=pipeline_kwargs,
    )


async def build_audit_report(session: AsyncSession, audit: AuditRun) -> AuditReportResponse:
    health_row = await HealthScoreRepository(session).get_by_audit(audit.id)
    executions = await EngineExecutionRepository(session).list_by_audit(audit.id)
    finding_repo = FindingRepository(session)
    severity_counts = await finding_repo.count_by_severity(audit.id)
    by_engine = await finding_repo.count_by_engine(audit.id)

    health_score: HealthScoreResponse | None = None
    category_scores: dict[str, int] | None = None
    if health_row is not None:
        category_scores = {
            "seo": health_row.seo_score or 0,
            "accessibility": health_row.accessibility_score or 0,
            "security": health_row.security_score or 0,
            "performance": health_row.performance_score or 0,
            "business": health_row.business_score or 0,
        }
        # Prefer JSON category_scores when present
        if health_row.category_scores:
            category_scores = {
                str(k): int(v) for k, v in health_row.category_scores.items()
            }
        health_score = HealthScoreResponse(
            overall_score=health_row.overall_score,
            category_scores=category_scores,
            grade=health_row.grade,
            confidence=health_row.confidence,
            breakdown=dict(health_row.breakdown or {}),
            configuration_version=health_row.configuration_version,
        )
    elif audit.health_score is not None:
        category_scores = {
            "seo": audit.seo_score or 0,
            "accessibility": audit.accessibility_score or 0,
            "security": audit.security_score or 0,
            "performance": audit.performance_score or 0,
            "business": audit.business_score or 0,
        }
        health_score = HealthScoreResponse(
            overall_score=audit.health_score,
            category_scores=category_scores,
            grade="N/A",
            confidence=audit.confidence_score or 0,
            breakdown={},
            configuration_version=audit.scoring_config_version or "",
        )

    rec_repo = RecommendationRepository(session)
    rec_rows = await rec_repo.list_by_audit(audit.id)
    recommendations: RecommendationSummaryResponse | None = None
    if rec_rows:
        priority_counts = await rec_repo.count_by_priority(audit.id)
        items = [
            RecommendationItemResponse(
                recommendation_id=row.recommendation_id,
                title=row.title,
                description=row.recommendation_text,
                technical_reason=row.technical_reason,
                business_reason=row.business_explanation,
                category=row.category,
                priority=row.priority,
                estimated_effort=row.estimated_effort,
                estimated_impact=row.estimated_impact,
                confidence=row.confidence,
                affected_findings=list(row.affected_findings or []),
                related_rules=list(row.related_rules or []),
                priority_score=float(row.priority_score or 0),
                is_quick_win=bool(row.is_quick_win),
                status=row.status,
            )
            for row in rec_rows
        ]
        recommendations = RecommendationSummaryResponse(
            items=items,
            priority_summary=PrioritySummaryResponse(
                critical=priority_counts.get("Critical", 0),
                high=priority_counts.get("High", 0),
                medium=priority_counts.get("Medium", 0),
                low=priority_counts.get("Low", 0),
                total=priority_counts.get("total", 0),
            ),
            quick_wins=[i.recommendation_id for i in items if i.is_quick_win],
            high_impact=[
                i.recommendation_id
                for i in items
                if i.estimated_impact in _HIGH_IMPACT
            ],
            long_term=[
                i.recommendation_id
                for i in items
                if i.estimated_effort in _LONG_TERM
            ],
            counts={
                "total": len(items),
                "quick_wins": sum(1 for i in items if i.is_quick_win),
                "high_impact": sum(1 for i in items if i.estimated_impact in _HIGH_IMPACT),
                "long_term": sum(1 for i in items if i.estimated_effort in _LONG_TERM),
            },
        )

    return AuditReportResponse(
        audit_id=audit.id,
        website_id=audit.website_id,
        url=audit.requested_url,
        canonical_url=audit.canonical_url,
        status=audit.status,
        progress=audit.progress_percent,
        current_engine=audit.current_engine,
        scores=AuditScoresResponse(
            overall=audit.health_score,
            seo=audit.seo_score,
            performance=audit.performance_score,
            security=audit.security_score,
            accessibility=audit.accessibility_score,
            business=audit.business_score,
            roi=audit.roi_score,
        ),
        health_score=health_score,
        category_scores=category_scores,
        engine_summary=[
            EngineSummaryItem(
                engine_name=row.engine_name,
                status=row.status,
                duration_ms=row.execution_time_ms,
                started_at=row.started_at,
                completed_at=row.completed_at,
                error_message=row.error_message,
            )
            for row in executions
        ],
        finding_counts=FindingCountsResponse(
            total=severity_counts.get("total", 0),
            critical=severity_counts.get("critical", 0),
            high=severity_counts.get("high", 0),
            medium=severity_counts.get("medium", 0),
            low=severity_counts.get("low", 0),
            info=severity_counts.get("info", 0),
            by_engine=by_engine,
        ),
        recommendations=recommendations,
        failure_code=audit.failure_code,
        failure_message=audit.failure_message,
        duration_ms=audit.duration_ms,
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        created_at=audit.created_at,
        updated_at=audit.updated_at,
    )


@router.post(
    "",
    response_model=AuditCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_audit(
    body: AuditCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSession,
    pipeline_factory: Annotated[PipelineFactory | None, Depends(get_pipeline_factory)],
    pipeline_kwargs: Annotated[dict[str, Any], Depends(get_pipeline_kwargs)],
) -> AuditCreateResponse:
    """
    Create an AuditRun and start the pipeline in the background.

    Returns quickly with ``pending`` so clients can poll ``GET /audits/{id}``
    for live ``progress`` / ``current_engine``. Pipeline logic is unchanged.
    """
    try:
        started = await StartAuditUseCase(session).execute(body.website_id)
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    # Persist pending row before the request ends so the background job can load it.
    await session.commit()

    schedule_audit_pipeline(
        request.app.state.session_factory,
        started.audit_run.id,
        pipeline_factory=pipeline_factory,
        pipeline_kwargs=pipeline_kwargs,
        background_tasks=background_tasks,
    )

    return AuditCreateResponse(
        audit_id=started.audit_run.id,
        status=started.audit_run.status,
        message="Audit created successfully.",
    )


@router.get(
    "/{audit_id}",
    response_model=AuditReportResponse,
)
async def get_audit(audit_id: UUID, session: DbSession) -> AuditReportResponse:
    audit = await AuditRepository(session).get_by_id(audit_id)
    if audit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "AUDIT_NOT_FOUND",
                "message": "Audit run not found or has been deleted.",
            },
        )
    return await build_audit_report(session, audit)


@router.get(
    "/{audit_id}/report",
    response_model=AuditReportDTO,
    tags=["reports"],
)
async def get_audit_full_report(audit_id: UUID, session: DbSession) -> AuditReportDTO:
    """Return the complete UI-ready report assembled from persisted artifacts."""
    try:
        result = await GetAuditReportUseCase(session).execute(audit_id)
    except AuditNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ReportNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return result.report


@router.post(
    "/{audit_id}/report/regenerate",
    response_model=AuditReportDTO,
    tags=["reports"],
)
async def regenerate_audit_report(audit_id: UUID, session: DbSession) -> AuditReportDTO:
    """Rebuild report projection from current persisted engine artifacts (no recrawl)."""
    try:
        result = await GetAuditReportUseCase(session).execute(
            audit_id,
            force_regenerate=True,
        )
    except AuditNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except ReportNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return result.report
