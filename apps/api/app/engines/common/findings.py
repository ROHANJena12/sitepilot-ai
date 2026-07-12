"""Shared Finding primitives for analysis engines (SEO, Accessibility, …)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """Finding severity (ENGINE_SPEC §4.4 / DOMAIN_MODEL)."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    """Finding emission status (ENGINE_SPEC uses fail/warn/pass)."""

    FAIL = "fail"
    WARN = "warn"
    INFO = "info"
    PASS = "pass"


class Finding(BaseModel):
    """
    Discrete observation produced by an analysis engine.

    Stable ``id`` values follow ``<engine>.<area>.<variant>`` and must not be
    renamed casually. ``category`` is a free-form label per engine taxonomy.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    rule_id: str
    category: str
    severity: Severity
    title: str
    description: str
    location: str | None = None
    element: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    status: FindingStatus = FindingStatus.FAIL
