"""Application-layer errors for AI explanation use cases."""

from __future__ import annotations


class AIApplicationError(Exception):
    """Base application error for AI HTTP orchestration."""

    code: str = "AI_APPLICATION_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)


class FindingNotFoundError(AIApplicationError):
    code = "FINDING_NOT_FOUND"


class RecommendationNotFoundError(AIApplicationError):
    code = "RECOMMENDATION_NOT_FOUND"


class AIFeatureUnavailableError(AIApplicationError):
    """Requested AI feature cannot run for this entity (e.g. not a quick win)."""

    code = "AI_FEATURE_UNAVAILABLE"


class GenerationNotFoundError(AIApplicationError):
    """No persisted AI generation for this entity / version."""

    code = "GENERATION_NOT_FOUND"


class JobNotFoundError(AIApplicationError):
    """No AI generation job for the given id."""

    code = "JOB_NOT_FOUND"


class JobNotCompleteError(AIApplicationError):
    """Job result requested before completion."""

    code = "JOB_NOT_COMPLETE"


class JobAlreadyRunningError(AIApplicationError):
    """Invalid transition — job is already running."""

    code = "JOB_ALREADY_RUNNING"


class JobAlreadyCompletedError(AIApplicationError):
    """Invalid transition — job is already completed."""

    code = "JOB_ALREADY_COMPLETED"
