"""Shared export contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.services.report.schemas import AuditReportDTO


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """Binary download payload with HTTP metadata."""

    content: bytes
    media_type: str
    filename: str


class ReportExporter(ABC):
    """Render an already-assembled ``AuditReportDTO`` into a downloadable file."""

    @abstractmethod
    def export(self, report: AuditReportDTO) -> ExportArtifact:
        """Produce file bytes from the report DTO (no I/O, no AI, no engines)."""


class ExportFailedError(Exception):
    """Exporter failed while rendering a ready report."""

    code = "EXPORT_FAILED"

    def __init__(self, message: str = "Report export failed.") -> None:
        self.message = message
        super().__init__(message)
