"""Recommendation persistence repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.recommendation.constants import MODEL_USED, PROVIDER, RULES_CONFIG_VERSION
from app.engines.recommendation.schemas import Recommendation, RecommendationAnalysis
from app.models.recommendation import RecommendationRow, RecommendationSource


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_audit(
        self,
        *,
        audit_run_id: UUID,
        analysis: RecommendationAnalysis,
        engine_execution_id: UUID | None = None,
        finding_meta: dict[str, dict[str, Any]] | None = None,
    ) -> list[RecommendationRow]:
        """Replace all recommendation rows for an audit with the latest analysis."""
        await self._session.execute(
            delete(RecommendationSource).where(
                RecommendationSource.audit_run_id == audit_run_id
            )
        )
        await self._session.execute(
            delete(RecommendationRow).where(RecommendationRow.audit_run_id == audit_run_id)
        )
        await self._session.flush()

        meta = finding_meta or {}
        rows: list[RecommendationRow] = []
        for rec in analysis.recommendations:
            row = self._to_row(
                audit_run_id=audit_run_id,
                rec=rec,
                engine_execution_id=engine_execution_id,
                config_version=analysis.configuration_version or RULES_CONFIG_VERSION,
            )
            self._session.add(row)
            await self._session.flush()
            for finding_id in rec.affected_findings:
                info = meta.get(finding_id, {})
                self._session.add(
                    RecommendationSource(
                        audit_run_id=audit_run_id,
                        recommendation_row_id=row.id,
                        finding_id=finding_id,
                        source_engine=info.get("engine"),
                        severity=info.get("severity"),
                        evidence=info.get("evidence") or {},
                    )
                )
            rows.append(row)
        await self._session.flush()
        return rows

    async def get_by_id(self, recommendation_row_id: UUID) -> RecommendationRow | None:
        """Load a recommendation by persisted row UUID (``recommendations.id``)."""
        result = await self._session.execute(
            select(RecommendationRow).where(
                RecommendationRow.id == recommendation_row_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_audit(self, audit_run_id: UUID) -> list[RecommendationRow]:
        result = await self._session.execute(
            select(RecommendationRow)
            .where(RecommendationRow.audit_run_id == audit_run_id)
            .order_by(
                RecommendationRow.priority_score.desc(),
                RecommendationRow.recommendation_id.asc(),
            )
        )
        return list(result.scalars().all())

    async def count_by_priority(self, audit_run_id: UUID) -> dict[str, int]:
        result = await self._session.execute(
            select(RecommendationRow.priority, func.count())
            .where(RecommendationRow.audit_run_id == audit_run_id)
            .group_by(RecommendationRow.priority)
        )
        counts = {p: 0 for p in ("Critical", "High", "Medium", "Low")}
        for priority, count in result.all():
            counts[str(priority)] = int(count)
        counts["total"] = sum(v for k, v in counts.items() if k != "total")
        return counts

    async def quick_win_ids(self, audit_run_id: UUID) -> list[str]:
        result = await self._session.execute(
            select(RecommendationRow.recommendation_id)
            .where(
                RecommendationRow.audit_run_id == audit_run_id,
                RecommendationRow.is_quick_win.is_(True),
            )
            .order_by(RecommendationRow.priority_score.desc())
        )
        return [str(r) for r in result.scalars().all()]

    def _to_row(
        self,
        *,
        audit_run_id: UUID,
        rec: Recommendation,
        engine_execution_id: UUID | None,
        config_version: str,
    ) -> RecommendationRow:
        primary_finding = rec.affected_findings[0] if rec.affected_findings else None
        return RecommendationRow(
            audit_run_id=audit_run_id,
            engine_execution_id=engine_execution_id,
            recommendation_id=rec.recommendation_id,
            finding_id=primary_finding,
            title=rec.title,
            recommendation_text=rec.description,
            technical_reason=rec.technical_reason,
            business_explanation=rec.business_reason,
            category=rec.category.value,
            priority=rec.priority.value,
            estimated_effort=rec.estimated_effort.value,
            estimated_impact=rec.estimated_impact.value,
            priority_score=rec.priority_score,
            confidence=rec.confidence,
            status="open",
            is_quick_win=rec.is_quick_win,
            affected_findings=list(rec.affected_findings),
            related_rules=list(rec.related_rules),
            prompt_version=config_version,
            model_used=MODEL_USED,
            provider=PROVIDER,
            version=1,
            raw_response=rec.model_dump(mode="python"),
            is_fallback=not rec.recommendation_id.startswith("rec.")
            or ":seo." in rec.recommendation_id
            or "generic" in rec.recommendation_id,
        )
