"""Organization ORM model — DATABASE_SPEC §6."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Index, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "plan_tier IN ('free', 'pro', 'business', 'agency', 'enterprise')",
            name="organizations_plan_tier_chk",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'closed')",
            name="organizations_status_chk",
        ),
        Index(
            "organizations_slug_uidx",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False)
    plan_tier: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'free'"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    billing_email: Mapped[str | None] = mapped_column(CITEXT, nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="organization",
        lazy="selectin",
    )
