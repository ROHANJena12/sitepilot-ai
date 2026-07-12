"""Centralized AI job retention & classification thresholds (Sprint 26.3)."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

# Retention — future cleanup workers reuse these. Nothing deletes rows in Sprint 26.3.
JOB_RETENTION_COMPLETED_DAYS = 1
JOB_RETENTION_FAILED_DAYS = 7
JOB_RETENTION_CANCELLED_DAYS = 7

# Completed jobs get expires_at = completed_at + this window.
JOB_COMPLETED_EXPIRES_AFTER = timedelta(hours=24)

# Running jobs older than this are considered stale (diagnostics only).
JOB_STALE_RUNNING_AFTER = timedelta(minutes=5)

# Execution duration presentation classes (from execution_ms).
DURATION_FAST_MS = 1_000
DURATION_NORMAL_MS = 5_000
DURATION_SLOW_MS = 30_000

# Queue wait presentation classes (from queue_wait_ms).
QUEUE_IMMEDIATE_MS = 100
QUEUE_SHORT_MS = 1_000
QUEUE_NORMAL_MS = 5_000


class DurationClass(StrEnum):
    FAST = "FAST"
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    VERY_SLOW = "VERY_SLOW"


class QueueClass(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    SHORT = "SHORT"
    NORMAL = "NORMAL"
    LONG = "LONG"
