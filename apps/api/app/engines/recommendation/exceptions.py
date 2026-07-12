"""Recommendation engine exceptions."""

from __future__ import annotations


class RecommendationError(Exception):
    """Base recommendation engine error."""

    code: str = "RECOMMENDATION_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class MissingAnalysisError(RecommendationError):
    code = "MISSING_ANALYSIS"

    def __init__(self, message: str, *, missing: tuple[str, ...] = ()) -> None:
        self.missing = missing
        super().__init__(message)


class InvalidAnalysisError(RecommendationError):
    code = "INVALID_ANALYSIS"


class TemplateNotFoundError(RecommendationError):
    code = "TEMPLATE_NOT_FOUND"


class ConfigurationError(RecommendationError):
    code = "CONFIGURATION_ERROR"
