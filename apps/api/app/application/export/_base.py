"""Shared export use-case base."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.get_report import GetAuditReportUseCase
from app.export.base import ExportArtifact, ExportFailedError, ReportExporter


@dataclass(frozen=True, slots=True)
class ExportReportResult:
    artifact: ExportArtifact


class ExportReportUseCase:
    """Load assembled report via GetAuditReportUseCase, then render with an exporter."""

    def __init__(self, session: AsyncSession, exporter: ReportExporter) -> None:
        self._get_report = GetAuditReportUseCase(session)
        self._exporter = exporter

    async def execute(self, audit_id: UUID) -> ExportReportResult:
        report_result = await self._get_report.execute(audit_id)
        try:
            artifact = self._exporter.export(report_result.report)
        except ExportFailedError:
            raise
        except Exception as exc:  # noqa: BLE001 — map renderer failures to EXPORT_FAILED
            raise ExportFailedError(f"Report export failed: {exc}") from exc
        return ExportReportResult(artifact=artifact)
