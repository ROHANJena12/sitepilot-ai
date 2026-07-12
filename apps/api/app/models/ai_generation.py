"""AIGeneration ORM — versioned AI explanation artifacts (Sprint 24)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin

_STATUS_CHK = ", ".join(f"'{s}'" for s in ("success", "cached", "error"))
_FEATURE_CHK = ", ".join(
    f"'{f}'"
    for f in (
        "finding",
        "recommendation",
        "executive_summary",
        "business_summary",
        "quick_win",
    )
)
_ENTITY_CHK = _FEATURE_CHK


class AIGeneration(Base, TimestampMixin):
    """
    Immutable persisted AI generation.

    Never update prior rows — new content inserts ``version + 1``.
    Identical content (same feature / entity / report_hash / response_hash)
    reuses the existing version.
    """

    __tablename__ = "ai_generations"
    __table_args__ = (
        UniqueConstraint(
            "feature",
            "entity_id",
            "report_hash",
            "version",
            name="ai_generations_feature_entity_report_ver_uidx",
        ),
        CheckConstraint(f"feature IN ({_FEATURE_CHK})", name="ai_generations_feature_chk"),
        CheckConstraint(
            f"entity_type IN ({_ENTITY_CHK})", name="ai_generations_entity_type_chk"
        ),
        CheckConstraint(f"status IN ({_STATUS_CHK})", name="ai_generations_status_chk"),
        CheckConstraint("version >= 1", name="ai_generations_version_chk"),
        Index("ai_generations_audit_idx", "audit_id"),
        Index("ai_generations_feature_idx", "feature"),
        Index("ai_generations_entity_idx", "entity_type", "entity_id"),
        Index("ai_generations_report_hash_idx", "report_hash"),
        Index("ai_generations_generation_id_idx", "generation_id"),
        Index("ai_generations_response_hash_idx", "response_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    generation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    builder_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_hash: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("''")
    )
    input_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_hash: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'en'"))
    response_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    telemetry_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    diagnostics_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'success'")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
