"""Report Composer — assemble persisted audit data into a UI-ready AuditReportDTO.

This is **not** an Engine. It does not join the pipeline. It performs no analysis,
scoring, recommendation generation, AI calls, or network I/O.
"""

from app.services.report.composer import ReportComposer
from app.services.report.constants import SCHEMA_VERSION
from app.services.report.schemas import AuditReportDTO

__all__ = [
    "AuditReportDTO",
    "ReportComposer",
    "SCHEMA_VERSION",
]
