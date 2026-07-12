"""Report repository — DATABASE_SPEC §16 projection persistence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_audit(self, audit_run_id: UUID) -> Report | None:
        result = await self._session.execute(
            select(Report).where(Report.audit_run_id == audit_run_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, report_id: UUID) -> Report | None:
        result = await self._session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def upsert_projection(
        self,
        *,
        audit_run_id: UUID,
        schema_version: str,
        executive_summary: str,
        business_summary: dict[str, Any],
        report_json: dict[str, Any],
        report_hash: str | None = None,
        report_version: int | None = None,
        charts: dict[str, Any] | None = None,
    ) -> Report:
        """
        Upsert report projection.

        ``version`` column stores ``report_version`` (generation counter).
        ``schema_version`` stores the JSON contract version.
        """
        existing = await self.get_by_audit(audit_run_id)
        if existing is None:
            row = Report(
                audit_run_id=audit_run_id,
                version=report_version or 1,
                status="ready",
                executive_summary=executive_summary,
                business_summary=business_summary,
                report_json=report_json,
                report_hash=report_hash,
                charts=charts or {},
                schema_version=schema_version,
            )
            self._session.add(row)
        else:
            row = existing
            if report_version is not None:
                row.version = report_version
            row.status = "ready"
            row.executive_summary = executive_summary
            row.business_summary = business_summary
            row.report_json = report_json
            row.report_hash = report_hash
            row.charts = charts if charts is not None else row.charts
            row.schema_version = schema_version
            self._session.add(row)

        await self._session.flush()
        await self._session.refresh(row)
        return row
