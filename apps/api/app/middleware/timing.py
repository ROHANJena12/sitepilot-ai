"""Request timing middleware."""

from __future__ import annotations

import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    header_name = "X-Process-Time-Ms"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers[self.header_name] = f"{elapsed_ms:.2f}"

        log_fields: dict = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(elapsed_ms, 2),
        }
        if response.status_code >= 500:
            log_fields["error_code"] = "SERVER_ERROR"
        elif response.status_code >= 400:
            log_fields["error_code"] = "CLIENT_ERROR"
        logger.info("request_completed", **log_fields)
        return response
