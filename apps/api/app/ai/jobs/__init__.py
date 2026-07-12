"""AI background job package — queue + worker (Sprint 26–27)."""

from __future__ import annotations

from app.ai.jobs.cancel_reason import CancelReason
from app.ai.jobs.factory import create_job_queue, normalize_queue_backend
from app.ai.jobs.failure import JobFailureCategory, classify_failure
from app.ai.jobs.identity import DEFAULT_WORKER_ID, LOCAL_WORKER_ID
from app.ai.jobs.lifecycle import (
    age_ms,
    classify_duration,
    classify_queue_wait,
    is_cleanup_candidate,
    is_expired,
    is_stale,
)
from app.ai.jobs.progress import JobProgress
from app.ai.jobs.queue import InMemoryQueue, QueueDiagnostics, QueuePort
from app.ai.jobs.redis_queue import RedisQueue
from app.ai.jobs.redis_worker import RedisWorker
from app.ai.jobs.retention import (
    JOB_RETENTION_CANCELLED_DAYS,
    JOB_RETENTION_COMPLETED_DAYS,
    JOB_RETENTION_FAILED_DAYS,
    DurationClass,
    QueueClass,
)
from app.ai.jobs.status import JobStatus
from app.ai.jobs.worker import BackgroundWorker

__all__ = [
    "BackgroundWorker",
    "CancelReason",
    "DEFAULT_WORKER_ID",
    "DurationClass",
    "InMemoryQueue",
    "JOB_RETENTION_CANCELLED_DAYS",
    "JOB_RETENTION_COMPLETED_DAYS",
    "JOB_RETENTION_FAILED_DAYS",
    "JobFailureCategory",
    "JobProgress",
    "JobStatus",
    "LOCAL_WORKER_ID",
    "QueueClass",
    "QueueDiagnostics",
    "QueuePort",
    "RedisQueue",
    "RedisWorker",
    "age_ms",
    "classify_duration",
    "classify_failure",
    "classify_queue_wait",
    "create_job_queue",
    "is_cleanup_candidate",
    "is_expired",
    "is_stale",
    "normalize_queue_backend",
]
