"""Configurable security response headers."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings

# FastAPI ships Swagger UI / ReDoc as HTML that loads scripts, styles, fonts,
# and images from public CDNs. A JSON API CSP of ``default-src 'none'`` blocks
# those assets and yields a blank /docs or /redoc page.
# /openapi.json stays on the strict API CSP — it is JSON, not an HTML UI.
_DOCS_PATH_PREFIXES = ("/docs", "/redoc")

# Relaxed CSP scoped to interactive API documentation only.
# Still forbids framing and limits script/style sources to known CDNs + self.
DOCS_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' https://fastapi.tiangolo.com data: https:; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def is_api_docs_path(path: str) -> bool:
    """Return True for FastAPI Swagger UI / ReDoc HTML routes only."""
    return any(
        path == prefix or path.startswith(f"{prefix}/")
        for prefix in _DOCS_PATH_PREFIXES
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Apply baseline browser security headers.

    REST responses (including ``/openapi.json``) keep the configured strict CSP
    (default ``default-src 'none'``). Interactive docs (``/docs``, ``/redoc``)
    receive a relaxed CSP so CDN-hosted Swagger/ReDoc assets can load. Other
    headers (frame options, referrer, permissions, HSTS) always apply.
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

        csp = (
            DOCS_CONTENT_SECURITY_POLICY
            if is_api_docs_path(request.url.path)
            else self._settings.security_csp
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        if self._settings.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security",
                self._settings.security_hsts_value,
            )
        return response
