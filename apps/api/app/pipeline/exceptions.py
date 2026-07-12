"""Pipeline orchestration exceptions."""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for pipeline / runtime failures."""

    def __init__(self, message: str, *, code: str = "PIPELINE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class RegistrationError(PipelineError):
    """Engine registry registration / lookup failure."""

    def __init__(self, message: str, *, code: str = "ENGINE_REGISTRATION_ERROR") -> None:
        super().__init__(message, code=code)


class EngineExecutionError(PipelineError):
    """A single engine raised or returned a fatal failure."""

    def __init__(
        self,
        message: str,
        *,
        engine_name: str,
        code: str = "ENGINE_EXECUTION_ERROR",
    ) -> None:
        super().__init__(message, code=code)
        self.engine_name = engine_name


class PipelineExecutionError(PipelineError):
    """Pipeline aborted (typically due to a fatal engine failure)."""

    def __init__(
        self,
        message: str,
        *,
        failed_engine: str | None = None,
        code: str = "PIPELINE_EXECUTION_ERROR",
    ) -> None:
        super().__init__(message, code=code)
        self.failed_engine = failed_engine
