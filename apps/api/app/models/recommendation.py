"""Recommendation ORM — DATABASE_SPEC §15 + Sprint 15 priority/effort fields."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin

_PRIORITY_CHK = ", ".join(f"'{p}'" for p in ("Critical", "High", "Medium", "Low"))
_EFFORT_CHK = ", ".join(
    f"'{e}'" for e in ("Very Low", "Low", "Medium", "High", "Very High")
)
_IMPACT_CHK = ", ".join(f"'{i}'" for i in ("Critical", "High", "Medium", "Low"))
_STATUS_CHK = ", ".join(
    f"'{s}'" for s in ("open", "accepted", "in_progress", "done", "dismissed")
)


class RecommendationRow(Base, TimestampMixin):
    """Persisted recommendation for one audit run."""

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(f"priority IN ({_PRIORITY_CHK})", name="recommendations_priority_chk"),
        CheckConstraint(f"estimated_effort IN ({_EFFORT_CHK})", name="recommendations_effort_chk"),
        CheckConstraint(f"estimated_impact IN ({_IMPACT_CHK})", name="recommendations_impact_chk"),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="recommendations_status_chk"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="recommendations_confidence_chk",
        ),
        UniqueConstraint(
            "audit_run_id",
            "recommendation_id",
            "version",
            name="recommendations_run_rec_ver_uidx",
        ),
        Index("recommendations_run_idx", "audit_run_id"),
        Index("recommendations_priority_idx", "audit_run_id", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    audit_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    engine_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engine_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_id: Mapped[str] = mapped_column(Text, nullable=False)
    finding_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    technical_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_effort: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_impact: Mapped[str] = mapped_column(Text, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, server_default=text("0"))
    confidence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'open'"))
    is_quick_win: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    affected_findings: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    related_rules: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class RecommendationSource(Base, TimestampMixin):
    """Links a recommendation to contributing findings."""

    __tablename__ = "recommendation_sources"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_row_id",
            "finding_id",
            name="recommendation_sources_row_finding_uidx",
        ),
        Index("recommendation_sources_run_idx", "audit_run_id"),
        Index("recommendation_sources_finding_idx", "finding_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    audit_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommendation_row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_engine: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
