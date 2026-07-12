"""Mutable audit execution context shared across engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.logging import get_logger


@dataclass
class AuditContext:
    """
    Mutable per-audit execution context.

    Engines may enrich ``normalized_url``, ``metadata``, and ``shared_state``.
    They must not import sibling engines — only the orchestrator sequences them.
    """

    audit_id: UUID
    website_id: UUID | None
    url: str
    normalized_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    shared_state: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    logger: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.logger is None:
            self.logger = get_logger("app.pipeline").bind(
                audit_id=str(self.audit_id),
                website_id=str(self.website_id) if self.website_id else None,
                correlation_id=self.correlation_id,
            )

    def bind_logger(self, **kwargs: Any) -> Any:
        """Return a child logger with additional bound fields."""
        return self.logger.bind(**kwargs)
