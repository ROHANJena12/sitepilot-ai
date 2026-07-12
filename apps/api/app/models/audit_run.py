"""AuditRun ORM model — DATABASE_SPEC §9 (+ Sprint 3 progress columns)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    desc,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin
from app.domain.audit_status import AUDIT_STATUS_VALUES

if TYPE_CHECKING:
    from app.models.website import Website

_STATUS_LIST = ", ".join(f"'{s}'" for s in AUDIT_STATUS_VALUES)


class AuditRun(Base, TimestampMixin, SoftDeleteMixin):
    """
    One row per website scan.

    Future EngineExecution relationship (placeholder — no engine tables in Sprint 3):
        engine_executions = relationship("EngineExecution", back_populates="audit_run")
    """

    __tablename__ = "audit_runs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({_STATUS_LIST})",
            name="audit_runs_status_chk",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="audit_runs_progress_chk",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="audit_runs_duration_chk",
        ),
        CheckConstraint(
            "health_score IS NULL OR (health_score BETWEEN 0 AND 100)",
            name="audit_runs_health_score_chk",
        ),
        CheckConstraint(
            "seo_score IS NULL OR (seo_score BETWEEN 0 AND 100)",
            name="audit_runs_seo_score_chk",
        ),
        CheckConstraint(
            "performance_score IS NULL OR (performance_score BETWEEN 0 AND 100)",
            name="audit_runs_performance_score_chk",
        ),
        CheckConstraint(
            "security_score IS NULL OR (security_score BETWEEN 0 AND 100)",
            name="audit_runs_security_score_chk",
        ),
        CheckConstraint(
            "accessibility_score IS NULL OR (accessibility_score BETWEEN 0 AND 100)",
            name="audit_runs_accessibility_score_chk",
        ),
        CheckConstraint(
            "business_score IS NULL OR (business_score BETWEEN 0 AND 100)",
            name="audit_runs_business_score_chk",
        ),
        CheckConstraint(
            "roi_score IS NULL OR (roi_score BETWEEN 0 AND 100)",
            name="audit_runs_roi_score_chk",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score BETWEEN 0 AND 100)",
            name="audit_runs_confidence_score_chk",
        ),
        Index("audit_runs_website_created_idx", "website_id", desc("created_at")),
        Index("audit_runs_org_status_idx", "organization_id", "status"),
        Index(
            "audit_runs_status_idx",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # FK to users deferred until auth sprint (DATABASE_SPEC: SET NULL on delete).
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    requested_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    # Sprint 3 polling fields (API_SPEC progress / current_step)
    current_engine: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("0"),
    )

    failure_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    health_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    seo_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    performance_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    security_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    accessibility_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    business_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    roi_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    confidence_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    scoring_config_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    pipeline_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    client_ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    website: Mapped[Website] = relationship(
        "Website",
        back_populates="audit_runs",
        lazy="joined",
    )
