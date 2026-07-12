"""AI generation job progress checkpoints (0–100)."""

from __future__ import annotations

from enum import IntEnum


class JobProgress(IntEnum):
    """Suggested lifecycle progress values."""

    QUEUED = 0
    LOADING = 10
    BUILDING_PROMPT = 20
    PROVIDER_REQUEST = 40
    GROUNDING = 70
    PERSISTING = 90
    COMPLETED = 100
