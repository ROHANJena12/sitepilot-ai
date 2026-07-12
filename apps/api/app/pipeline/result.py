"""Engine and pipeline result models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EngineStatus(StrEnum):
    """Per-engine execution status (ENGINE_SPEC §4.3)."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(StrEnum):
    """Aggregate pipeline outcome."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class EngineResult(BaseModel):
    """
    Standardized outcome of one engine ``run(context)`` invocation.

    Engines never decide sibling skip/retry policy — the runtime does.
    """

    model_config = ConfigDict(frozen=True)

    engine_name: str
    status: EngineStatus
    duration_ms: int = Field(ge=0)
    success: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        engine_name: str,
        *,
        duration_ms: int,
        payload: dict[str, Any] | None = None,
        warnings: tuple[str, ...] = (),
    ) -> EngineResult:
        return cls(
            engine_name=engine_name,
            status=EngineStatus.SUCCESS,
            duration_ms=duration_ms,
            success=True,
            warnings=warnings,
            errors=(),
            payload=payload or {},
        )

    @classmethod
    def fail(
        cls,
        engine_name: str,
        *,
        duration_ms: int,
        errors: tuple[str, ...],
        payload: dict[str, Any] | None = None,
        warnings: tuple[str, ...] = (),
    ) -> EngineResult:
        return cls(
            engine_name=engine_name,
            status=EngineStatus.FAILED,
            duration_ms=duration_ms,
            success=False,
            warnings=warnings,
            errors=errors,
            payload=payload or {},
        )


class PipelineResult(BaseModel):
    """Aggregate outcome of a sequential pipeline run."""

    model_config = ConfigDict(frozen=True)

    overall_status: PipelineStatus
    completed_engines: tuple[str, ...] = ()
    failed_engine: str | None = None
    results: tuple[EngineResult, ...] = ()
    total_duration: int = Field(ge=0, description="Total wall time in milliseconds")
