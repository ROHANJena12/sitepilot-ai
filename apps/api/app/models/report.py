"""Report ORM — DATABASE_SPEC §16."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin

_STATUS_CHK = ", ".join(f"'{s}'" for s in ("ready", "generating_pdf", "failed"))


class Report(Base, TimestampMixin):
    """Assembled customer-facing report projection for one audit run."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("audit_run_id", name="reports_audit_run_uidx"),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="reports_status_chk"),
        CheckConstraint("version >= 1", name="reports_version_chk"),
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
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'ready'"))
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    report_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_json_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    charts: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    schema_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'report.v1'"),
    )
