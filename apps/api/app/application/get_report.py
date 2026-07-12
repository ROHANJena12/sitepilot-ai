"""Get assembled Audit Report use-case."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.report.composer import ReportComposer
from app.services.report.schemas import AuditReportDTO


@dataclass(frozen=True, slots=True)
class GetReportResult:
    report: AuditReportDTO


class GetAuditReportUseCase:
    """Compose (or return cached projection of) the UI-ready audit report."""

    def __init__(self, session: AsyncSession) -> None:
        self._composer = ReportComposer(session)

    async def execute(
        self,
        audit_id: UUID,
        *,
        force_regenerate: bool = False,
    ) -> GetReportResult:
        report = await self._composer.compose(
            audit_id,
            force_regenerate=force_regenerate,
        )
        return GetReportResult(report=report)
