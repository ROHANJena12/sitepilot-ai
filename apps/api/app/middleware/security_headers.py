"""Configurable security response headers."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Apply baseline browser security headers.

    HSTS is only set when ``settings.security_enable_hsts`` is true
    (typically production behind HTTPS).
    """

    def __init__(self, app, settings: Settings) -> None:  # noqa: ANN001
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if not self._settings.security_headers_enabled:
            return response

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", self._settings.security_x_frame_options)
        response.headers.setdefault("Referrer-Policy", self._settings.security_referrer_policy)
        response.headers.setdefault(
            "Permissions-Policy",
            self._settings.security_permissions_policy,
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            self._settings.security_csp,
        )
        if self._settings.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security",
                self._settings.security_hsts_value,
            )
        return response
