"""HTTP error mapping for AI orchestration."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    InvalidAIResponse,
    ServiceNotReady,
)
from app.api.v1.ai.errors import raise_http_from_ai_orchestration
from app.application.ai.exceptions import (
    AIFeatureUnavailableError,
    FindingNotFoundError,
    RecommendationNotFoundError,
)
from app.services.report.exceptions import AuditNotFoundError, ReportNotReadyError


def _code(exc: HTTPException) -> str:
    assert isinstance(exc.detail, dict)
    return str(exc.detail["code"])


@pytest.mark.parametrize(
    ("err", "status", "code"),
    [
        (AuditNotFoundError("x"), 404, "AUDIT_NOT_FOUND"),
        (FindingNotFoundError("x"), 404, "FINDING_NOT_FOUND"),
        (RecommendationNotFoundError("x"), 404, "RECOMMENDATION_NOT_FOUND"),
        (ReportNotReadyError("x"), 409, "REPORT_NOT_READY"),
        (AIFeatureUnavailableError("x"), 409, "AI_FEATURE_UNAVAILABLE"),
        (InvalidAIResponse("x"), 422, "INVALID_AI_RESPONSE"),
        (AIProviderError("x"), 503, "UPSTREAM_UNAVAILABLE"),
        (AIConfigurationError("x"), 503, "NOT_READY"),
        (ServiceNotReady("x"), 503, "NOT_READY"),
    ],
)
def test_error_mapping(err: Exception, status: int, code: str) -> None:
    with pytest.raises(HTTPException) as caught:
        raise_http_from_ai_orchestration(err)
    assert caught.value.status_code == status
    assert _code(caught.value) == code
