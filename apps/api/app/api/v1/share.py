"""Report sharing HTTP endpoints — signed, read-only presentation links."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.application.share_report import (
    CreateShareLinkUseCase,
    GetSharedReportUseCase,
    ShareTokenExpired,
    ShareTokenInvalid,
)
from app.core.config import get_settings
from app.dependencies.db import DbSession
from app.schemas.share import ShareLinkResponse
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError
from app.services.report.schemas import AuditReportDTO

audits_share_router = APIRouter(prefix="/audits", tags=["share"])
share_router = APIRouter(prefix="/share", tags=["share"])


def _raise_share_http(exc: Exception) -> None:
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
    if isinstance(exc, ShareTokenExpired):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    if isinstance(exc, ShareTokenInvalid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    raise exc


@audits_share_router.post(
    "/{audit_id}/share",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a read-only share link for an audit report",
)
async def create_audit_share_link(
    audit_id: UUID,
    session: DbSession,
    request: Request,
) -> ShareLinkResponse:
    """
    Mint a signed, time-limited share URL for a completed report.

    Does not regenerate the report — only verifies it is available, then signs
    a token. Recipients use ``GET /api/v1/share/{token}`` (read-only).
    """
    settings = getattr(request.app.state, "settings", None) or get_settings()
    use_case = CreateShareLinkUseCase(session, settings=settings)
    try:
        result = await use_case.execute(audit_id)
    except (AuditNotFoundError, ReportNotReadyError) as exc:
        _raise_share_http(exc)
        raise  # pragma: no cover

    share_url = result.share_url
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") in {
        o.rstrip("/") for o in settings.cors_origins
    }:
        share_url = f"{origin.rstrip('/')}/share/{result.token}"

    return ShareLinkResponse(
        share_url=share_url,
        token=result.token,
        expires_at=result.expires_at,
        audit_id=str(result.audit_id),
    )


@share_router.get(
    "/{token}",
    response_model=AuditReportDTO,
    summary="Fetch a report via signed share token (read-only)",
)
async def get_shared_report(
    token: str,
    session: DbSession,
    request: Request,
) -> AuditReportDTO:
    """
    Resolve a share token to ``AuditReportDTO``.

    Reuses ``GetAuditReportUseCase``. No AI, export, or regenerate on this path.
    """
    settings = getattr(request.app.state, "settings", None) or get_settings()
    try:
        result = await GetSharedReportUseCase(session, settings=settings).execute(token)
    except (ShareTokenInvalid, ShareTokenExpired, AuditNotFoundError, ReportNotReadyError) as exc:
        _raise_share_http(exc)
        raise  # pragma: no cover
    return result.report
