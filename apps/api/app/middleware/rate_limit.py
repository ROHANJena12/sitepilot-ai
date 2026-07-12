"""Lightweight path-based rate limiting for public write endpoints."""

from __future__ import annotations

import re
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.rate_limit import get_rate_limiter
from app.schemas.errors import ErrorBody, ErrorEnvelope

_AI_GENERATE = re.compile(
    r"^/api/v1/(?:audits|findings|recommendations)/[^/]+/ai/"
    r"(?:generate|generate-executive-summary|generate-business-summary|"
    r"generate-quick-win|regenerate|regenerate-executive-summary|"
    r"regenerate-business-summary|regenerate-quick-win)(?:/)?$",
)
_AUDIT_CREATE = re.compile(r"^/api/v1/audits/?$")
_SHARE_CREATE = re.compile(r"^/api/v1/audits/[^/]+/share/?$")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # noqa: ANN001
        super().__init__(app)
        self._settings = settings
        self._limiter = get_rate_limiter()

    def _rule_for(self, method: str, path: str) -> tuple[str, int, int] | None:
        if not self._settings.rate_limit_enabled:
            return None
        if method == "POST" and _AUDIT_CREATE.match(path):
            return (
                "audits",
                self._settings.rate_limit_audits_limit,
                self._settings.rate_limit_audits_window_seconds,
            )
        if method == "POST" and _SHARE_CREATE.match(path):
            return (
                "share",
                self._settings.rate_limit_share_limit,
                self._settings.rate_limit_share_window_seconds,
            )
        if method == "POST" and _AI_GENERATE.match(path):
            return (
                "ai",
                self._settings.rate_limit_ai_limit,
                self._settings.rate_limit_ai_window_seconds,
            )
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rule = self._rule_for(request.method, request.url.path)
        if rule is None:
            return await call_next(request)

        bucket, limit, window = rule
        ip = _client_ip(request)
        result = self._limiter.check(f"{bucket}:{ip}", limit=limit, window_seconds=window)
        if not result.allowed:
            payload = ErrorEnvelope(
                error=ErrorBody(
                    code="RATE_LIMITED",
                    message=(
                        "Too many requests from this IP. Please wait and try again."
                    ),
                    request_id=getattr(request.state, "request_id", None),
                    retry_after=result.retry_after,
                )
            )
            response = JSONResponse(
                status_code=429,
                content=payload.model_dump(exclude_none=True),
            )
            response.headers["Retry-After"] = str(result.retry_after or 60)
            response.headers["X-RateLimit-Limit"] = str(result.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(result.reset_at)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)
        return response
