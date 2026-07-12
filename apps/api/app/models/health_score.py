"""HealthScore ORM — Sprint 14 persistence of Health Score Engine output."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class HealthScore(Base, TimestampMixin):
    """Persisted health score snapshot for one audit run (1:1)."""

    __tablename__ = "health_scores"
    __table_args__ = (
        UniqueConstraint("audit_run_id", name="health_scores_audit_run_uidx"),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="health_scores_overall_chk",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="health_scores_confidence_chk",
        ),
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
    overall_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    seo_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    accessibility_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    security_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    business_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    grade: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    category_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    penalties: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    configuration_version: Mapped[str] = mapped_column(Text, nullable=False)
