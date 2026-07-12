"""Create / resolve read-only report share links."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.get_report import GetAuditReportUseCase, GetReportResult
from app.core.config import Settings, get_settings
from app.core.signed_tokens import (
    TokenExpiredError,
    TokenInvalidError,
    sign_payload,
    verify_token,
)
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError

SHARE_TOKEN_SALT = "sitepilot-report-share-v1"


class ShareLinkError(Exception):
    code: str = "SHARE_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class ShareTokenInvalid(ShareLinkError):
    code = "SHARE_TOKEN_INVALID"


class ShareTokenExpired(ShareLinkError):
    code = "SHARE_TOKEN_EXPIRED"


@dataclass(frozen=True, slots=True)
class CreateShareLinkResult:
    share_url: str
    token: str
    expires_at: datetime
    audit_id: UUID


class CreateShareLinkUseCase:
    """
    Issue a signed, time-limited share token for a completed report.

    Verifies the report is available via ``GetAuditReportUseCase`` (no duplicate
    composition logic). Does not persist tokens.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._reports = GetAuditReportUseCase(session)

    async def execute(self, audit_id: UUID) -> CreateShareLinkResult:
        # Ensure report exists / is ready before minting a link.
        await self._reports.execute(audit_id)

        ttl = self._settings.share_token_ttl_seconds
        token, exp_unix = sign_payload(
            {"aid": str(audit_id)},
            secret=self._settings.secret_key,
            salt=SHARE_TOKEN_SALT,
            ttl_seconds=ttl,
        )
        base = self._settings.public_web_url.rstrip("/")
        share_url = f"{base}/share/{token}"
        expires_at = datetime.fromtimestamp(exp_unix, tz=UTC)
        return CreateShareLinkResult(
            share_url=share_url,
            token=token,
            expires_at=expires_at,
            audit_id=audit_id,
        )


class GetSharedReportUseCase:
    """
    Resolve a share token and return the assembled report.

    Reuses ``GetAuditReportUseCase`` — never rebuilds composer logic.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._reports = GetAuditReportUseCase(session)

    async def execute(self, token: str) -> GetReportResult:
        try:
            payload = verify_token(
                token,
                secret=self._settings.secret_key,
                salt=SHARE_TOKEN_SALT,
            )
        except TokenExpiredError as exc:
            raise ShareTokenExpired(str(exc)) from exc
        except TokenInvalidError as exc:
            raise ShareTokenInvalid(str(exc)) from exc

        raw_id = payload.get("aid")
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise ShareTokenInvalid("Invalid share token.")
        try:
            audit_id = UUID(raw_id)
        except ValueError as exc:
            raise ShareTokenInvalid("Invalid share token.") from exc

        try:
            return await self._reports.execute(audit_id)
        except (AuditNotFoundError, ReportNotReadyError) as exc:
            # Do not leak existence details for shared links.
            raise ShareTokenInvalid("Shared report is unavailable.") from exc
