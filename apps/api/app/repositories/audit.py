"""AuditRun repository — persistence only (DATABASE_SPEC §9)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_status import AuditStatus
from app.models.audit_run import AuditRun
from app.repositories.base import get_active_by_id, not_deleted, utcnow


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, audit_run: AuditRun) -> AuditRun:
        self._session.add(audit_run)
        await self._session.flush()
        await self._session.refresh(audit_run)
        return audit_run

    async def get_by_id(self, audit_id: UUID) -> AuditRun | None:
        return await get_active_by_id(self._session, AuditRun, audit_id)

    async def update_status(
        self,
        audit_id: UUID,
        status: AuditStatus | str,
        *,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> AuditRun | None:
        audit = await self.get_by_id(audit_id)
        if audit is None:
            return None

        status_value = status.value if isinstance(status, AuditStatus) else status
        audit.status = status_value
        if failure_code is not None:
            audit.failure_code = failure_code
        if failure_message is not None:
            audit.failure_message = failure_message
        if (
            audit.started_at is None
            and status_value
            not in {
                AuditStatus.PENDING.value,
                AuditStatus.COMPLETE.value,
                AuditStatus.COMPLETE_WITH_WARNINGS.value,
                AuditStatus.FAILED.value,
                AuditStatus.CANCELLED.value,
            }
        ):
            audit.started_at = utcnow()

        self._session.add(audit)
        await self._session.flush()
        await self._session.refresh(audit)
        return audit

    async def update_progress(
        self,
        audit_id: UUID,
        *,
        progress_percent: int,
        current_engine: str | None = None,
        status: AuditStatus | str | None = None,
    ) -> AuditRun | None:
        audit = await self.get_by_id(audit_id)
        if audit is None:
            return None

        if not 0 <= progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")

        audit.progress_percent = progress_percent
        if current_engine is not None:
            audit.current_engine = current_engine
        if status is not None:
            status_value = status.value if isinstance(status, AuditStatus) else status
            audit.status = status_value
            if audit.started_at is None and status_value != AuditStatus.PENDING.value:
                audit.started_at = utcnow()

        self._session.add(audit)
        await self._session.flush()
        await self._session.refresh(audit)
        return audit

    async def list_by_website(
        self,
        website_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditRun]:
        stmt = (
            not_deleted(AuditRun)
            .where(AuditRun.website_id == website_id)
            .order_by(AuditRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_completed(
        self,
        audit_id: UUID,
        *,
        health_score: int | None = None,
        seo_score: int | None = None,
        performance_score: int | None = None,
        security_score: int | None = None,
        accessibility_score: int | None = None,
        business_score: int | None = None,
        roi_score: int | None = None,
        confidence_score: int | None = None,
        with_warnings: bool = False,
        completed_at: datetime | None = None,
    ) -> AuditRun | None:
        audit = await self.get_by_id(audit_id)
        if audit is None:
            return None

        finished_at = completed_at or utcnow()
        audit.status = (
            AuditStatus.COMPLETE_WITH_WARNINGS.value
            if with_warnings
            else AuditStatus.COMPLETE.value
        )
        audit.completed_at = finished_at
        audit.progress_percent = 100
        audit.current_engine = None
        if audit.started_at is not None:
            audit.duration_ms = int((finished_at - audit.started_at).total_seconds() * 1000)
        elif audit.duration_ms is None:
            audit.duration_ms = 0

        if health_score is not None:
            audit.health_score = health_score
        if seo_score is not None:
            audit.seo_score = seo_score
        if performance_score is not None:
            audit.performance_score = performance_score
        if security_score is not None:
            audit.security_score = security_score
        if accessibility_score is not None:
            audit.accessibility_score = accessibility_score
        if business_score is not None:
            audit.business_score = business_score
        if roi_score is not None:
            audit.roi_score = roi_score
        if confidence_score is not None:
            audit.confidence_score = confidence_score

        self._session.add(audit)
        await self._session.flush()
        await self._session.refresh(audit)
        return audit

    async def mark_failed(
        self,
        audit_id: UUID,
        *,
        failure_code: str,
        failure_message: str,
        completed_at: datetime | None = None,
    ) -> AuditRun | None:
        audit = await self.get_by_id(audit_id)
        if audit is None:
            return None

        finished_at = completed_at or utcnow()
        audit.status = AuditStatus.FAILED.value
        audit.failure_code = failure_code
        audit.failure_message = failure_message
        audit.completed_at = finished_at
        if audit.started_at is not None:
            audit.duration_ms = int((finished_at - audit.started_at).total_seconds() * 1000)

        self._session.add(audit)
        await self._session.flush()
        await self._session.refresh(audit)
        return audit
