"""JSON export — exact AuditReportDTO serialization."""

from __future__ import annotations

from app.export.base import ExportArtifact, ReportExporter
from app.services.report.schemas import AuditReportDTO


class JsonReportExporter(ReportExporter):
    """Return the report DTO as UTF-8 JSON with no field transforms."""

    def export(self, report: AuditReportDTO) -> ExportArtifact:
        payload = report.model_dump_json(by_alias=True)
        return ExportArtifact(
            content=payload.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            filename="audit-report.json",
        )
