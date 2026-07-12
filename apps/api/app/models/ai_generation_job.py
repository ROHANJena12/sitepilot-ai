"""AIGenerationJob ORM — async AI generation jobs (Sprint 26 / 26.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

_STATUS_VALUES = ("queued", "running", "completed", "failed", "cancelled")
_STATUS_CHK = ", ".join(f"'{s}'" for s in _STATUS_VALUES)
_FEATURE_VALUES = (
    "finding",
    "recommendation",
    "executive_summary",
    "business_summary",
    "quick_win",
)
_FEATURE_CHK = ", ".join(f"'{f}'" for f in _FEATURE_VALUES)
_ENTITY_CHK = _FEATURE_CHK
_CANCEL_REASONS = (
    "USER_REQUESTED",
    "TIMEOUT",
    "SHUTDOWN",
    "PROVIDER_FAILURE",
    "DUPLICATE",
    "SUPERSEDED",
)
_CANCEL_CHK = ", ".join(f"'{r}'" for r in _CANCEL_REASONS)
_FAILURE_CATEGORIES = (
    "UNKNOWN",
    "VALIDATION",
    "GROUNDING",
    "PROVIDER",
    "TIMEOUT",
    "PERSISTENCE",
    "QUEUE",
    "USER_CANCELLED",
    "INTERNAL",
)
_FAILURE_CHK = ", ".join(f"'{c}'" for c in _FAILURE_CATEGORIES)


class AIGenerationJob(Base):
    """
    Durable AI generation job — separate from ``ai_generations``.

    Lifecycle: queued → running → completed | failed.
    Cancelled is terminal when cancelled while queued.
    """

    __tablename__ = "ai_generation_jobs"
    __table_args__ = (
        CheckConstraint(f"feature IN ({_FEATURE_CHK})", name="ai_generation_jobs_feature_chk"),
        CheckConstraint(
            f"entity_type IN ({_ENTITY_CHK})", name="ai_generation_jobs_entity_type_chk"
        ),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="ai_generation_jobs_status_chk"),
        CheckConstraint("attempt >= 0", name="ai_generation_jobs_attempt_chk"),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ai_generation_jobs_progress_chk",
        ),
        CheckConstraint("max_attempts >= 1", name="ai_generation_jobs_max_attempts_chk"),
        CheckConstraint(
            f"cancel_reason IS NULL OR cancel_reason IN ({_CANCEL_CHK})",
            name="ai_generation_jobs_cancel_reason_chk",
        ),
        CheckConstraint(
            f"failure_category IS NULL OR failure_category IN ({_FAILURE_CHK})",
            name="ai_generation_jobs_failure_category_chk",
        ),
        Index("ai_generation_jobs_status_idx", "status"),
        Index("ai_generation_jobs_feature_entity_idx", "feature", "entity_id"),
        Index("ai_generation_jobs_audit_idx", "audit_id"),
        Index("ai_generation_jobs_created_idx", "created_at"),
        Index("ai_generation_jobs_queued_idx", "queued_at"),
        Index("ai_generation_jobs_expires_idx", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    # API path UUID (finding row / recommendation row / audit) for generate use cases.
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_hash: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'queued'")
    )
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    worker: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase_history: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    failure_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
