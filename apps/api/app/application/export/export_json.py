"""Export JSON use-case."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.export._base import ExportReportResult, ExportReportUseCase
from app.export.json_exporter import JsonReportExporter


class ExportJsonUseCase(ExportReportUseCase):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, JsonReportExporter())


__all__ = ["ExportJsonUseCase", "ExportReportResult"]
