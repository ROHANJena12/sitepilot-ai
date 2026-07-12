"""Job observability helpers — phases, events, summary, health (Sprint 26.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.ai.jobs.progress import JobProgress
from app.models.ai_generation_job import AIGenerationJob


class JobEventType(StrEnum):
    QUEUED = "QUEUED"
    STARTED = "STARTED"
    PROVIDER_STARTED = "PROVIDER_STARTED"
    GROUNDING_STARTED = "GROUNDING_STARTED"
    PERSIST_STARTED = "PERSIST_STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


_PROGRESS_TO_PHASE: dict[int, str] = {
    int(JobProgress.LOADING): "loading",
    int(JobProgress.BUILDING_PROMPT): "building_prompt",
    int(JobProgress.PROVIDER_REQUEST): "provider_request",
    int(JobProgress.GROUNDING): "grounding",
    int(JobProgress.PERSISTING): "persisting",
}


def phase_name_for_progress(progress: int) -> str | None:
    return _PROGRESS_TO_PHASE.get(int(progress))


def new_phase_entry(
    phase: str,
    *,
    started_at: datetime,
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    ended = completed_at or datetime.now(UTC)
    duration_ms = max(0, int((ended - started_at).total_seconds() * 1000))
    return {
        "phase": phase,
        "name": phase,
        "started_at": started_at.isoformat(),
        "completed_at": ended.isoformat(),
        "duration_ms": duration_ms,
    }


def normalize_phase_history(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or item.get("name") or "")
        if not phase:
            continue
        entry = {
            "phase": phase,
            "name": str(item.get("name") or phase),
            "duration_ms": int(item["duration_ms"]) if item.get("duration_ms") is not None else None,
        }
        if item.get("started_at") is not None:
            entry["started_at"] = item["started_at"]
        if item.get("completed_at") is not None:
            entry["completed_at"] = item["completed_at"]
        diagnostics = item.get("diagnostics")
        if isinstance(diagnostics, dict) and diagnostics:
            entry["diagnostics"] = diagnostics
        out.append(entry)
    return out


def compute_status_summary(job: AIGenerationJob) -> str:
    status = job.status
    if status == "queued":
        return "Queued"
    if status == "completed":
        return "Completed"
    if status == "failed":
        return "Failed"
    if status == "cancelled":
        return "Cancelled"
    if status == "running":
        progress = int(job.progress or 0)
        if progress >= int(JobProgress.PERSISTING):
            return "Persisting"
        if progress >= int(JobProgress.GROUNDING):
            return "Grounding response"
        if progress >= int(JobProgress.PROVIDER_REQUEST):
            return "Waiting for provider"
        if progress >= int(JobProgress.BUILDING_PROMPT):
            return "Building prompt"
        return "Running"
    return status.replace("_", " ").title()


def compute_job_events(job: AIGenerationJob) -> list[dict[str, Any]]:
    """Derive timeline events from timestamps / progress / status (not persisted)."""
    events: list[dict[str, Any]] = []
    queued_at = job.queued_at or job.created_at
    if queued_at is not None:
        events.append(
            {
                "event": JobEventType.QUEUED.value,
                "at": queued_at.isoformat() if hasattr(queued_at, "isoformat") else str(queued_at),
            }
        )
    if job.started_at is not None:
        events.append(
            {
                "event": JobEventType.STARTED.value,
                "at": job.started_at.isoformat(),
            }
        )
    progress = int(job.progress or 0)
    if progress >= int(JobProgress.PROVIDER_REQUEST) or job.status in (
        "completed",
        "failed",
    ):
        at = job.started_at or queued_at
        events.append(
            {
                "event": JobEventType.PROVIDER_STARTED.value,
                "at": at.isoformat() if at is not None and hasattr(at, "isoformat") else None,
            }
        )
    if progress >= int(JobProgress.GROUNDING) or job.status == "completed":
        at = job.completed_at or job.started_at
        events.append(
            {
                "event": JobEventType.GROUNDING_STARTED.value,
                "at": at.isoformat() if at is not None and hasattr(at, "isoformat") else None,
            }
        )
    if progress >= int(JobProgress.PERSISTING) or job.status == "completed":
        at = job.completed_at or job.started_at
        events.append(
            {
                "event": JobEventType.PERSIST_STARTED.value,
                "at": at.isoformat() if at is not None and hasattr(at, "isoformat") else None,
            }
        )
    if job.status == "completed" and job.completed_at is not None:
        events.append(
            {"event": JobEventType.COMPLETED.value, "at": job.completed_at.isoformat()}
        )
    elif job.status == "failed" and job.completed_at is not None:
        events.append(
            {"event": JobEventType.FAILED.value, "at": job.completed_at.isoformat()}
        )
    elif job.status == "cancelled" and job.completed_at is not None:
        events.append(
            {"event": JobEventType.CANCELLED.value, "at": job.completed_at.isoformat()}
        )
    return events


def compute_health(job: AIGenerationJob) -> dict[str, bool]:
    status = job.status
    return {
        "is_running": status == "running",
        "is_terminal": status in ("completed", "failed", "cancelled"),
        "is_success": status == "completed",
        "is_failure": status == "failed",
    }


def extract_provider_diagnostics(
    response_json: dict[str, Any] | None,
    phase_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Mirror lightweight fields from stored AIResponse metadata (not new DB columns).

    Falls back to bounded ``provider_diagnostics`` entries written into
    ``phase_history`` on failed provider calls (Sprint 30.2).
    """
    body = response_json or {}
    meta = body.get("provider_metadata") if isinstance(body.get("provider_metadata"), dict) else {}
    quality = body.get("quality") if isinstance(body.get("quality"), dict) else {}
    telemetry = body.get("telemetry") if isinstance(body.get("telemetry"), dict) else {}

    cached = meta.get("cached")
    if cached is None:
        cached = quality.get("cache_hit")

    latency = meta.get("latency_ms")
    if latency is None:
        latency = meta.get("provider_latency_ms")
    if latency is None:
        latency = telemetry.get("latency_ms")

    finish_reason = meta.get("finish_reason")
    if finish_reason is None:
        finish_reason = telemetry.get("finish_reason")

    retry_count = meta.get("retry_count")
    if retry_count is None:
        retry_count = telemetry.get("retry_count")

    provider = meta.get("provider") or quality.get("provider")
    model = meta.get("model") or quality.get("model")

    if (provider is None or model is None or latency is None or finish_reason is None) and phase_history:
        for entry in reversed(phase_history):
            if not isinstance(entry, dict):
                continue
            if entry.get("phase") not in ("provider_diagnostics", "provider_request"):
                continue
            diag = entry.get("diagnostics")
            if not isinstance(diag, dict):
                continue
            provider = provider or diag.get("provider")
            model = model or diag.get("model")
            finish_reason = finish_reason or diag.get("finish_reason")
            if latency is None:
                total = diag.get("total_provider_ms")
                if isinstance(total, (int, float)):
                    latency = int(total)
                elif isinstance(entry.get("duration_ms"), (int, float)):
                    latency = int(entry["duration_ms"])
            if provider is not None and model is not None:
                break

    return {
        "provider": provider,
        "model": model,
        "latency_ms": latency,
        "cached": bool(cached) if cached is not None else None,
        "finish_reason": finish_reason,
        "retry_count": retry_count,
    }
