"""Lifecycle events emitted around engine execution (observability hooks)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.pipeline.result import EngineResult, EngineStatus


@dataclass(frozen=True, slots=True)
class EngineStarted:
    """Emitted immediately before an engine runs."""

    audit_id: UUID
    engine_name: str
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class EngineCompleted:
    """Emitted after a successful or partial engine run."""

    audit_id: UUID
    engine_name: str
    status: EngineStatus
    duration_ms: int
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class EngineFailed:
    """Emitted when an engine fails fatally for the pipeline."""

    audit_id: UUID
    engine_name: str
    duration_ms: int
    errors: tuple[str, ...]
    correlation_id: str | None = None


def event_to_log_fields(event: EngineStarted | EngineCompleted | EngineFailed) -> dict[str, Any]:
    """Flatten an event into structlog-friendly fields."""
    base: dict[str, Any] = {
        "audit_id": str(event.audit_id),
        "engine_name": event.engine_name,
        "correlation_id": event.correlation_id,
        "event_type": type(event).__name__,
    }
    if isinstance(event, EngineCompleted):
        base["status"] = event.status.value
        base["duration_ms"] = event.duration_ms
    elif isinstance(event, EngineFailed):
        base["duration_ms"] = event.duration_ms
        base["errors"] = list(event.errors)
    return base
