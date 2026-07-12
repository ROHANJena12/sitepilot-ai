"""Cancellation reasons for AI generation jobs."""

from __future__ import annotations

from enum import StrEnum


class CancelReason(StrEnum):
    USER_REQUESTED = "USER_REQUESTED"
    TIMEOUT = "TIMEOUT"
    SHUTDOWN = "SHUTDOWN"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    DUPLICATE = "DUPLICATE"
    SUPERSEDED = "SUPERSEDED"
