"""HealthScore repository — Sprint 14 persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_score import HealthScore


class HealthScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_for_audit(
        self,
        *,
        audit_run_id: UUID,
        overall_score: int,
        grade: str,
        confidence: int,
        configuration_version: str,
        seo_score: int | None = None,
        accessibility_score: int | None = None,
        security_score: int | None = None,
        performance_score: int | None = None,
        business_score: int | None = None,
        category_scores: dict[str, Any] | None = None,
        breakdown: dict[str, Any] | None = None,
        penalties: dict[str, Any] | list[Any] | None = None,
    ) -> HealthScore:
        existing = await self.get_by_audit(audit_run_id)
        if existing is None:
            row = HealthScore(
                audit_run_id=audit_run_id,
                overall_score=overall_score,
                seo_score=seo_score,
                accessibility_score=accessibility_score,
                security_score=security_score,
                performance_score=performance_score,
                business_score=business_score,
                grade=grade,
                confidence=confidence,
                category_scores=category_scores or {},
                breakdown=breakdown or {},
                penalties=penalties if isinstance(penalties, dict) else {"items": penalties or []},
                configuration_version=configuration_version,
            )
            self._session.add(row)
        else:
            row = existing
            row.overall_score = overall_score
            row.seo_score = seo_score
            row.accessibility_score = accessibility_score
            row.security_score = security_score
            row.performance_score = performance_score
            row.business_score = business_score
            row.grade = grade
            row.confidence = confidence
            row.category_scores = category_scores or {}
            row.breakdown = breakdown or {}
            row.penalties = (
                penalties if isinstance(penalties, dict) else {"items": penalties or []}
            )
            row.configuration_version = configuration_version
            self._session.add(row)

        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_audit(self, audit_run_id: UUID) -> HealthScore | None:
        result = await self._session.execute(
            select(HealthScore).where(HealthScore.audit_run_id == audit_run_id)
        )
        return result.scalar_one_or_none()
