"""Report Composer — assemble persisted audit artifacts into AuditReportDTO."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_run import AuditRun
from app.models.health_score import HealthScore
from app.models.report import Report
from app.repositories.audit import AuditRepository
from app.repositories.engine_execution import EngineExecutionRepository
from app.repositories.finding import FindingRepository
from app.repositories.health_score import HealthScoreRepository
from app.repositories.recommendation import RecommendationRepository
from app.repositories.report import ReportRepository
from app.repositories.website import WebsiteRepository
from app.services.report.builder import build_report_dto, ordered_category_scores
from app.services.report.constants import SCHEMA_VERSION
from app.services.report.exceptions import AuditNotFoundError
from app.services.report.hashing import compute_report_hash
from app.services.report.schemas import AuditReportDTO, HealthSectionDTO
from app.services.report.serializers import (
    dto_to_jsonable,
    serialize_engine,
    serialize_finding,
    serialize_recommendation,
    serialize_website,
)
from app.services.report.validators import assert_audit_ready_for_report


class ReportComposer:
    """
    Post-pipeline composer.

    Loads persisted AuditRun artifacts via repositories and assembles a
    UI-ready ``AuditReportDTO``. Performs no analysis, scoring, or AI.
    Persists the projection to ``reports`` for later cache/reuse.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audits = AuditRepository(session)
        self._websites = WebsiteRepository(session)
        self._findings = FindingRepository(session)
        self._health = HealthScoreRepository(session)
        self._recommendations = RecommendationRepository(session)
        self._executions = EngineExecutionRepository(session)
        self._reports = ReportRepository(session)

    async def compose(
        self,
        audit_id: UUID,
        *,
        force_regenerate: bool = False,
    ) -> AuditReportDTO:
        """
        Compose (or return previously persisted) report for an audit.

        Regeneration compares SHA-256 content hashes and skips version bumps
        when the underlying projection is unchanged.
        """
        audit = await self._audits.get_by_id(audit_id)
        if audit is None:
            raise AuditNotFoundError("Audit run not found or has been deleted.")

        assert_audit_ready_for_report(audit)
        existing = await self._reports.get_by_audit(audit_id)

        if not force_regenerate:
            if (
                existing is not None
                and existing.schema_version == SCHEMA_VERSION
                and existing.report_json
            ):
                # Backfill hash on legacy rows without rewriting content.
                if not existing.report_hash:
                    existing.report_hash = compute_report_hash(dict(existing.report_json))
                    self._session.add(existing)
                    await self._session.flush()
                return self._hydrate_cached(existing)

        dto = await self._build_fresh(audit)
        return await self._persist_smart(
            audit_id=audit.id,
            existing=existing,
            dto=dto,
        )

    async def regenerate(self, audit_id: UUID) -> AuditReportDTO:
        """Rebuild from current persisted artifacts (smart hash compare)."""
        return await self.compose(audit_id, force_regenerate=True)

    def _hydrate_cached(self, existing: Report) -> AuditReportDTO:
        dto = AuditReportDTO.model_validate(existing.report_json)
        report_version = int(existing.version)
        report_hash = existing.report_hash or dto.report_hash
        return dto.model_copy(
            update={
                "report_id": existing.id,
                "schema_version": existing.schema_version or SCHEMA_VERSION,
                "report_version": report_version,
                "report_hash": report_hash,
                "metadata": dto.metadata.model_copy(
                    update={
                        "report_id": existing.id,
                        "schema_version": existing.schema_version or SCHEMA_VERSION,
                        "report_version": report_version,
                        "report_hash": report_hash,
                        "generated_at": dto.generated_at,
                    }
                ),
            }
        )

    async def _persist_smart(
        self,
        *,
        audit_id: UUID,
        existing: Report | None,
        dto: AuditReportDTO,
    ) -> AuditReportDTO:
        provisional = dto_to_jsonable(dto)
        content_hash = compute_report_hash(provisional)

        if existing is not None:
            stored_hash = existing.report_hash
            if stored_hash is None and existing.report_json:
                stored_hash = compute_report_hash(dict(existing.report_json))

            if stored_hash == content_hash:
                # Identical content — do not update report_json or bump version.
                if existing.report_hash != stored_hash:
                    existing.report_hash = stored_hash
                    self._session.add(existing)
                    await self._session.flush()
                return self._hydrate_cached(existing)

            report_version = int(existing.version) + 1
        else:
            report_version = 1

        generated_at = datetime.now(UTC)
        dto = dto.model_copy(
            update={
                "report_version": report_version,
                "report_hash": content_hash,
                "generated_at": generated_at,
                "metadata": dto.metadata.model_copy(
                    update={
                        "report_version": report_version,
                        "report_hash": content_hash,
                        "generated_at": generated_at,
                    }
                ),
            }
        )
        # report_version / generated_at / report_hash are excluded from the digest,
        # so content_hash remains valid after attaching those fields.
        report_json = dto_to_jsonable(dto)

        saved = await self._reports.upsert_projection(
            audit_run_id=audit_id,
            schema_version=SCHEMA_VERSION,
            executive_summary=dto.summary,
            business_summary={
                "quick_wins": [r.recommendation_id for r in dto.quick_wins],
                "critical_issues": [f.id for f in dto.critical_issues],
                "summary_counts": dto.overview.summary_counts,
            },
            report_json=report_json,
            report_hash=content_hash,
            report_version=report_version,
        )
        return dto.model_copy(
            update={
                "report_id": saved.id,
                "report_version": saved.version,
                "report_hash": saved.report_hash,
                "metadata": dto.metadata.model_copy(
                    update={
                        "report_id": saved.id,
                        "report_version": saved.version,
                        "report_hash": saved.report_hash,
                    }
                ),
            }
        )

    async def _build_fresh(self, audit: AuditRun) -> AuditReportDTO:
        website = await self._websites.get_by_id(audit.website_id)
        website_meta = serialize_website(
            website,
            website_id=audit.website_id,
            fallback_url=audit.requested_url,
            canonical_url=audit.canonical_url,
        )

        finding_rows = await self._findings.list_by_audit(audit.id)
        rec_rows = await self._recommendations.list_by_audit(audit.id)
        exec_rows = await self._executions.list_by_audit(audit.id)
        health_row = await self._health.get_by_audit(audit.id)

        findings = [serialize_finding(r) for r in finding_rows]
        recommendations = [serialize_recommendation(r) for r in rec_rows]
        engines = [serialize_engine(r) for r in exec_rows]
        health = self._health_section(audit, health_row)

        rec_config = None
        if rec_rows:
            rec_config = rec_rows[0].prompt_version

        return build_report_dto(
            audit_id=audit.id,
            audit_status=audit.status,
            website=website_meta,
            started_at=audit.started_at,
            completed_at=audit.completed_at,
            duration_ms=audit.duration_ms,
            health=health,
            findings=findings,
            recommendations=recommendations,
            engines=engines,
            scoring_config_version=audit.scoring_config_version,
            recommendation_config_version=rec_config,
        )

    def _health_section(
        self,
        audit: AuditRun,
        health_row: HealthScore | None,
    ) -> HealthSectionDTO:
        if health_row is not None:
            merged = {
                "seo": health_row.seo_score if health_row.seo_score is not None else 0,
                "accessibility": (
                    health_row.accessibility_score
                    if health_row.accessibility_score is not None
                    else 0
                ),
                "security": (
                    health_row.security_score if health_row.security_score is not None else 0
                ),
                "performance": (
                    health_row.performance_score
                    if health_row.performance_score is not None
                    else 0
                ),
                "business": (
                    health_row.business_score if health_row.business_score is not None else 0
                ),
            }
            if health_row.category_scores:
                merged.update({str(k): int(v) for k, v in health_row.category_scores.items()})
            return HealthSectionDTO(
                overall_score=health_row.overall_score,
                grade=health_row.grade,
                confidence=health_row.confidence,
                category_scores=ordered_category_scores(merged),
                breakdown=dict(health_row.breakdown or {}),
                configuration_version=health_row.configuration_version,
            )

        return HealthSectionDTO(
            overall_score=audit.health_score,
            grade=None,
            confidence=audit.confidence_score,
            category_scores=ordered_category_scores(
                {
                    "seo": audit.seo_score or 0,
                    "accessibility": audit.accessibility_score or 0,
                    "security": audit.security_score or 0,
                    "performance": audit.performance_score or 0,
                    "business": audit.business_score or 0,
                }
            ),
            breakdown={},
            configuration_version=audit.scoring_config_version,
        )
