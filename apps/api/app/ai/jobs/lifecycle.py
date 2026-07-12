"""AI job lifecycle helpers — expiration, cleanup, stale, age, classes (Sprint 26.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.ai.jobs.retention import (
    DURATION_FAST_MS,
    DURATION_NORMAL_MS,
    DURATION_SLOW_MS,
    JOB_COMPLETED_EXPIRES_AFTER,
    JOB_RETENTION_CANCELLED_DAYS,
    JOB_RETENTION_COMPLETED_DAYS,
    JOB_RETENTION_FAILED_DAYS,
    JOB_STALE_RUNNING_AFTER,
    QUEUE_IMMEDIATE_MS,
    QUEUE_NORMAL_MS,
    QUEUE_SHORT_MS,
    DurationClass,
    QueueClass,
)
from app.models.ai_generation_job import AIGenerationJob


def default_expires_at(completed_at: datetime) -> datetime:
    """Default expiry for completed jobs: completed_at + 24 hours."""
    return completed_at + JOB_COMPLETED_EXPIRES_AFTER


def is_expired(job: AIGenerationJob, *, now: datetime | None = None) -> bool:
    """
    Completed jobs expire after ``expires_at``.

    Queued / running jobs never expire.
    """
    if job.status != "completed":
        return False
    expires_at = job.expires_at
    if expires_at is None and job.completed_at is not None:
        expires_at = default_expires_at(job.completed_at)
    if expires_at is None:
        return False
    current = now or datetime.now(UTC)
    if expires_at.tzinfo is None and current.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return current >= expires_at


def is_stale(job: AIGenerationJob, *, now: datetime | None = None) -> bool:
    """Running jobs whose ``started_at`` is older than the stale threshold."""
    if job.status != "running" or job.started_at is None:
        return False
    current = now or datetime.now(UTC)
    started = job.started_at
    if started.tzinfo is None and current.tzinfo is not None:
        started = started.replace(tzinfo=UTC)
    return current - started >= JOB_STALE_RUNNING_AFTER


def age_ms(job: AIGenerationJob, *, now: datetime | None = None) -> int:
    """Milliseconds since ``created_at``."""
    current = now or datetime.now(UTC)
    created = job.created_at
    if created.tzinfo is None and current.tzinfo is not None:
        created = created.replace(tzinfo=UTC)
    return max(0, int((current - created).total_seconds() * 1000))


def is_cleanup_candidate(job: AIGenerationJob, *, now: datetime | None = None) -> bool:
    """
    Eligible for future cleanup (no deletion performed here).

    - completed AND expired
    - failed older than failed retention
    - cancelled older than cancelled retention
    """
    current = now or datetime.now(UTC)
    if job.status == "completed":
        return is_expired(job, now=current)

    if job.status == "failed":
        return _older_than_days(
            job.completed_at or job.created_at,
            JOB_RETENTION_FAILED_DAYS,
            now=current,
        )

    if job.status == "cancelled":
        return _older_than_days(
            job.completed_at or job.created_at,
            JOB_RETENTION_CANCELLED_DAYS,
            now=current,
        )

    return False


def classify_duration(execution_ms: int | None) -> str | None:
    if execution_ms is None:
        return None
    if execution_ms < DURATION_FAST_MS:
        return DurationClass.FAST.value
    if execution_ms < DURATION_NORMAL_MS:
        return DurationClass.NORMAL.value
    if execution_ms < DURATION_SLOW_MS:
        return DurationClass.SLOW.value
    return DurationClass.VERY_SLOW.value


def classify_queue_wait(queue_wait_ms: int | None) -> str | None:
    if queue_wait_ms is None:
        return None
    if queue_wait_ms < QUEUE_IMMEDIATE_MS:
        return QueueClass.IMMEDIATE.value
    if queue_wait_ms < QUEUE_SHORT_MS:
        return QueueClass.SHORT.value
    if queue_wait_ms < QUEUE_NORMAL_MS:
        return QueueClass.NORMAL.value
    return QueueClass.LONG.value


def _older_than_days(
    anchor: datetime | None,
    days: int,
    *,
    now: datetime,
) -> bool:
    if anchor is None:
        return False
    point = anchor
    if point.tzinfo is None and now.tzinfo is not None:
        point = point.replace(tzinfo=UTC)
    return now - point >= timedelta(days=days)


# Re-export retention completed days for docs/tests (expires window is hours).
__all__ = [
    "JOB_RETENTION_CANCELLED_DAYS",
    "JOB_RETENTION_COMPLETED_DAYS",
    "JOB_RETENTION_FAILED_DAYS",
    "age_ms",
    "classify_duration",
    "classify_queue_wait",
    "default_expires_at",
    "is_cleanup_candidate",
    "is_expired",
    "is_stale",
]
