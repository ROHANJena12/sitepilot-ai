"""Export PDF use-case."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.export._base import ExportReportResult, ExportReportUseCase
from app.export.pdf_exporter import PdfReportExporter


class ExportPdfUseCase(ExportReportUseCase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PdfReportExporter())


__all__ = ["ExportPdfUseCase", "ExportReportResult"]
