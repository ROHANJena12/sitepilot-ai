"""Global exception handlers and API error envelope (API_SPEC §15)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.errors import ErrorBody, ErrorEnvelope

logger = get_logger(__name__)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(
    *,
    code: str,
    message: str,
    status_code: int,
    request: Request,
    details: dict[str, Any] | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            details=details,
            request_id=_request_id(request),
            retry_after=retry_after,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(exclude_none=True))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            code = str(detail["code"])
            message = str(detail["message"])
            details = {k: v for k, v in detail.items() if k not in {"code", "message"}} or None
        elif isinstance(detail, str):
            message = detail
            details = None
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                code = "NOT_FOUND"
            elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
                code = "UNAUTHORIZED"
            elif exc.status_code == status.HTTP_403_FORBIDDEN:
                code = "FORBIDDEN"
            elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                code = "RATE_LIMITED"
            else:
                code = "HTTP_ERROR"
        else:
            message = "Request failed"
            details = detail if isinstance(detail, dict) else None
            code = "NOT_FOUND" if exc.status_code == status.HTTP_404_NOT_FOUND else "HTTP_ERROR"

        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            code=code,
            path=str(request.url.path),
            request_id=_request_id(request),
        )
        return error_response(
            code=code,
            message=message,
            status_code=exc.status_code,
            request=request,
            details=details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "validation_error",
            path=str(request.url.path),
            errors=exc.errors(),
            request_id=_request_id(request),
        )
        return error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request=request,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            path=str(request.url.path),
            request_id=_request_id(request),
            error=str(exc),
        )
        return error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request=request,
        )
