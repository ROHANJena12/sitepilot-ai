"""Report Composer exceptions."""

from __future__ import annotations


class ReportError(Exception):
    """Base report composer error."""

    code: str = "REPORT_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class AuditNotFoundError(ReportError):
    code = "AUDIT_NOT_FOUND"


class ReportNotReadyError(ReportError):
    code = "REPORT_NOT_READY"


class ReportCompositionError(ReportError):
    code = "REPORT_COMPOSITION_ERROR"
