"""Website ORM model — DATABASE_SPEC §8."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.audit_run import AuditRun
    from app.models.project import Project


class Website(Base, TimestampMixin, SoftDeleteMixin):
    """Durable site identity under a Project."""

    __tablename__ = "websites"
    __table_args__ = (
        Index(
            "websites_project_canonical_uidx",
            "project_id",
            "canonical_url",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("websites_host_idx", "host"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    technology_stack: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_last_seen: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_https: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="websites",
        lazy="joined",
    )
    audit_runs: Mapped[list[AuditRun]] = relationship(
        "AuditRun",
        back_populates="website",
        lazy="selectin",
    )
