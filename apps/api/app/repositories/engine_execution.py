"""EngineExecution repository — DATABASE_SPEC §11."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engine_execution import EngineExecution
from app.repositories.base import utcnow


class EngineExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_running(
        self,
        *,
        audit_run_id: UUID,
        engine_name: str,
        engine_version: str = "0.1.0",
        attempt: int = 1,
        started_at: datetime | None = None,
    ) -> EngineExecution:
        row = EngineExecution(
            audit_run_id=audit_run_id,
            engine_name=engine_name,
            engine_version=engine_version,
            attempt=attempt,
            status="running",
            started_at=started_at or utcnow(),
            configuration={},
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def complete(
        self,
        execution_id: UUID,
        *,
        status: str,
        execution_time_ms: int,
        error_code: str | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
    ) -> EngineExecution | None:
        row = await self.get_by_id(execution_id)
        if row is None:
            return None
        row.status = status
        row.execution_time_ms = execution_time_ms
        row.completed_at = completed_at or utcnow()
        row.error_code = error_code
        row.error_message = error_message
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, execution_id: UUID) -> EngineExecution | None:
        result = await self._session.execute(
            select(EngineExecution).where(EngineExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def list_by_audit(self, audit_run_id: UUID) -> list[EngineExecution]:
        result = await self._session.execute(
            select(EngineExecution)
            .where(EngineExecution.audit_run_id == audit_run_id)
            .order_by(EngineExecution.started_at.asc().nulls_last(), EngineExecution.created_at.asc())
        )
        return list(result.scalars().all())
