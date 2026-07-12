"""Health Score Engine exceptions."""

from __future__ import annotations


class HealthScoreError(Exception):
    """Base class for health score engine failures."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class MissingAnalysisError(HealthScoreError):
    def __init__(
        self,
        message: str = "Upstream analyses are required in shared_state.",
        *,
        code: str = "MISSING_ANALYSIS",
        missing: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message, code=code)
        self.missing = missing


class InvalidAnalysisError(HealthScoreError):
    def __init__(
        self,
        message: str = "Upstream analysis must expose a findings collection.",
        *,
        code: str = "INVALID_ANALYSIS",
    ) -> None:
        super().__init__(message, code=code)


class InvalidScoringConfigError(HealthScoreError):
    def __init__(
        self,
        message: str = "Scoring configuration is invalid.",
        *,
        code: str = "INVALID_SCORING_CONFIG",
    ) -> None:
        super().__init__(message, code=code)
