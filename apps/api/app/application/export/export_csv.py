"""Export CSV use-case."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.export._base import ExportReportResult, ExportReportUseCase
from app.export.csv_exporter import CsvReportExporter


class ExportCsvUseCase(ExportReportUseCase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CsvReportExporter())


__all__ = ["ExportCsvUseCase", "ExportReportResult"]
