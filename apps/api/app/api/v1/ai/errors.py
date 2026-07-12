"""Map application / AI exceptions to HTTPException (API_SPEC §15)."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

from app.ai.exceptions import (
    AIConfigurationError,
    AIError,
    AIProviderError,
    GenerationNotImplemented,
    InvalidAIResponse,
    ProviderNotFound,
    ServiceNotReady,
)
from app.application.ai.exceptions import (
    AIFeatureUnavailableError,
    FindingNotFoundError,
    GenerationNotFoundError,
    JobAlreadyCompletedError,
    JobAlreadyRunningError,
    JobNotCompleteError,
    JobNotFoundError,
    RecommendationNotFoundError,
)
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError


def raise_http_from_ai_orchestration(exc: BaseException) -> NoReturn:
    """Translate use-case / AI failures into the standard error envelope detail."""
    if isinstance(exc, AuditNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, FindingNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, RecommendationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, GenerationNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, JobNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, JobNotCompleteError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, (JobAlreadyRunningError, JobAlreadyCompletedError)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, ReportNotReadyError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, AIFeatureUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, GenerationNotImplemented):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "AI_FEATURE_UNAVAILABLE",
                "message": exc.message,
            },
        ) from exc

    if isinstance(exc, InvalidAIResponse):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    if isinstance(exc, (AIConfigurationError, ServiceNotReady)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "NOT_READY", "message": exc.message},
        ) from exc

    if isinstance(exc, (AIProviderError, ProviderNotFound)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "UPSTREAM_UNAVAILABLE", "message": exc.message},
        ) from exc

    if isinstance(exc, AIError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "UPSTREAM_UNAVAILABLE", "message": exc.message},
        ) from exc

    raise exc


# Shared OpenAPI error response docs for AI endpoints.
AI_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    400: {
        "description": (
            "Invalid job transition (`JOB_ALREADY_RUNNING`, `JOB_ALREADY_COMPLETED`)."
        ),
    },
    404: {
        "description": (
            "Resource not found (`AUDIT_NOT_FOUND`, `FINDING_NOT_FOUND`, "
            "`RECOMMENDATION_NOT_FOUND`, `GENERATION_NOT_FOUND`, or `JOB_NOT_FOUND`)."
        ),
    },
    409: {
        "description": (
            "Conflict — audit not complete (`REPORT_NOT_READY`), AI feature "
            "unavailable (`AI_FEATURE_UNAVAILABLE`), or job not complete "
            "(`JOB_NOT_COMPLETE`)."
        ),
    },
    422: {
        "description": (
            "AI output failed schema or closed-world grounding validation "
            "(`INVALID_AI_RESPONSE`)."
        ),
    },
    503: {
        "description": (
            "Provider unavailable / timeout (`UPSTREAM_UNAVAILABLE`) or "
            "configuration missing (`NOT_READY`)."
        ),
    },
}
