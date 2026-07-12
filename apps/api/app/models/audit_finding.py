"""AuditFinding ORM — DATABASE_SPEC §14 (Sprint 14 persistence)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin

_SEVERITY_CHK = ", ".join(f"'{s}'" for s in ("critical", "high", "medium", "low", "info"))
_STATUS_CHK = ", ".join(f"'{s}'" for s in ("pass", "fail", "warn", "info", "skip", "error"))


class AuditFinding(Base, TimestampMixin):
    """Normalized finding row extracted from analysis engines."""

    __tablename__ = "audit_findings"
    __table_args__ = (
        CheckConstraint(f"severity IN ({_SEVERITY_CHK})", name="audit_findings_severity_chk"),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="audit_findings_status_chk"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="audit_findings_confidence_chk",
        ),
        UniqueConstraint("audit_run_id", "finding_id", name="audit_findings_run_finding_uidx"),
        Index("audit_findings_run_idx", "audit_run_id"),
        Index("audit_findings_category_sev_idx", "category", "severity"),
        Index("audit_findings_engine_idx", "engine_name"),
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
    engine_name: Mapped[str] = mapped_column(Text, nullable=False)
    finding_id: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("100"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'fail'"))
    issue: Mapped[str] = mapped_column(Text, nullable=False)  # title
    technical_detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # description
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    resolution_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'open'"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
