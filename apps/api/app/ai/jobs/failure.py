"""AI job failure classification (Sprint 26.2)."""

from __future__ import annotations

from enum import StrEnum


class JobFailureCategory(StrEnum):
    UNKNOWN = "UNKNOWN"
    VALIDATION = "VALIDATION"
    GROUNDING = "GROUNDING"
    PROVIDER = "PROVIDER"
    TIMEOUT = "TIMEOUT"
    PERSISTENCE = "PERSISTENCE"
    QUEUE = "QUEUE"
    USER_CANCELLED = "USER_CANCELLED"
    INTERNAL = "INTERNAL"


def classify_failure(exc: BaseException | None, *, message: str | None = None) -> JobFailureCategory:
    """Map an exception / error message to a failure category (best-effort)."""
    if exc is None and not message:
        return JobFailureCategory.UNKNOWN

    text = (message or (str(exc) if exc is not None else "") or "").strip()
    lower = text.lower()

    # Lazy imports keep AIService / providers out of this module's import graph.
    from app.ai.exceptions import (
        AIConfigurationError,
        AIProviderError,
        InvalidAIResponse,
        ServiceNotReady,
    )
    from app.application.ai.exceptions import (
        AIFeatureUnavailableError,
        FindingNotFoundError,
        JobAlreadyCompletedError,
        JobAlreadyRunningError,
        RecommendationNotFoundError,
    )
    from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError

    if isinstance(exc, InvalidAIResponse):
        if "ground" in lower:
            return JobFailureCategory.GROUNDING
        return JobFailureCategory.VALIDATION

    if isinstance(exc, AIProviderError):
        if "timeout" in lower or "timed out" in lower:
            return JobFailureCategory.TIMEOUT
        return JobFailureCategory.PROVIDER

    if isinstance(
        exc,
        (
            FindingNotFoundError,
            RecommendationNotFoundError,
            AuditNotFoundError,
            ReportNotReadyError,
            AIFeatureUnavailableError,
            JobAlreadyRunningError,
            JobAlreadyCompletedError,
        ),
    ):
        return JobFailureCategory.VALIDATION

    if isinstance(exc, (AIConfigurationError, ServiceNotReady)):
        return JobFailureCategory.INTERNAL

    if "timeout" in lower or "timed out" in lower:
        return JobFailureCategory.TIMEOUT
    if "ground" in lower:
        return JobFailureCategory.GROUNDING
    if "persist" in lower or "database" in lower or "sqlalchemy" in lower:
        return JobFailureCategory.PERSISTENCE
    if "queue" in lower:
        return JobFailureCategory.QUEUE
    if "cancel" in lower:
        return JobFailureCategory.USER_CANCELLED
    if "provider" in lower or "openai" in lower or "upstream" in lower:
        return JobFailureCategory.PROVIDER

    if exc is not None and not isinstance(exc, Exception):
        return JobFailureCategory.INTERNAL

    return JobFailureCategory.UNKNOWN if exc is None else JobFailureCategory.INTERNAL
