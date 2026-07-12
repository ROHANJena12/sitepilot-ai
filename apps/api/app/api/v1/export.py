"""Report export HTTP endpoints (PDF / JSON / CSV downloads)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.export import (
    ExportCsvUseCase,
    ExportFailedError,
    ExportJsonUseCase,
    ExportPdfUseCase,
)
from app.dependencies.db import get_db_session
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError

router = APIRouter(prefix="/audits", tags=["export"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _file_response(*, content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _raise_export_http(exc: Exception) -> None:
    if isinstance(exc, AuditNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    if isinstance(exc, ReportNotReadyError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    if isinstance(exc, ExportFailedError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    raise exc


@router.get("/{audit_id}/export/pdf")
async def export_audit_pdf(audit_id: UUID, session: DbSession) -> Response:
    """Download the assembled audit report as a PDF attachment."""
    try:
        result = await ExportPdfUseCase(session).execute(audit_id)
    except (AuditNotFoundError, ReportNotReadyError, ExportFailedError) as exc:
        _raise_export_http(exc)
        raise  # pragma: no cover
    artifact = result.artifact
    return _file_response(
        content=artifact.content,
        media_type=artifact.media_type,
        filename=artifact.filename,
    )


@router.get("/{audit_id}/export/json")
async def export_audit_json(audit_id: UUID, session: DbSession) -> Response:
    """Download the assembled AuditReportDTO as JSON (no transforms)."""
    try:
        result = await ExportJsonUseCase(session).execute(audit_id)
    except (AuditNotFoundError, ReportNotReadyError, ExportFailedError) as exc:
        _raise_export_http(exc)
        raise  # pragma: no cover
    artifact = result.artifact
    return _file_response(
        content=artifact.content,
        media_type=artifact.media_type,
        filename=artifact.filename,
    )


@router.get("/{audit_id}/export/csv")
async def export_audit_csv(audit_id: UUID, session: DbSession) -> Response:
    """Download findings and recommendations as UTF-8 CSV."""
    try:
        result = await ExportCsvUseCase(session).execute(audit_id)
    except (AuditNotFoundError, ReportNotReadyError, ExportFailedError) as exc:
        _raise_export_http(exc)
        raise  # pragma: no cover
    artifact = result.artifact
    return _file_response(
        content=artifact.content,
        media_type=artifact.media_type,
        filename=artifact.filename,
    )
