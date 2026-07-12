"""EngineExecution ORM — DATABASE_SPEC §11."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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

_ENGINE_NAMES = (
    "url_validation",
    "crawler",
    "parser",
    "html_parser",
    "seo",
    "seo_intelligence",
    "accessibility",
    "security",
    "performance",
    "business",
    "business_impact",
    "health",
    "health_score",
    "recommendation",
    "roi",
    "data_quality",
    "ai_recommendation",
    "report_builder",
    "pdf",
)
_ENGINE_CHK = ", ".join(f"'{n}'" for n in _ENGINE_NAMES)
_STATUS_CHK = ", ".join(
    f"'{s}'" for s in ("pending", "running", "success", "partial", "failed", "skipped")
)


class EngineExecution(Base, TimestampMixin):
    """One engine invocation bound to an audit run."""

    __tablename__ = "engine_executions"
    __table_args__ = (
        CheckConstraint(f"engine_name IN ({_ENGINE_CHK})", name="engine_executions_name_chk"),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="engine_executions_status_chk"),
        CheckConstraint(
            "execution_time_ms IS NULL OR execution_time_ms >= 0",
            name="engine_executions_duration_chk",
        ),
        UniqueConstraint(
            "audit_run_id",
            "engine_name",
            "attempt",
            name="engine_executions_run_engine_attempt_uidx",
        ),
        Index("engine_executions_run_idx", "audit_run_id"),
        Index("engine_executions_name_status_idx", "engine_name", "status"),
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
    engine_name: Mapped[str] = mapped_column(Text, nullable=False)
    engine_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'0.1.0'"))
    attempt: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    input_artifact_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
