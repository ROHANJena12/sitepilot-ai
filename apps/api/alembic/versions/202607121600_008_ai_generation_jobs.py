"""Create ai_generation_jobs table (Sprint 26 — async AI generation jobs).

Revision ID: 202607121600_008
Revises: 202607121500_007
Create Date: 2026-07-12 16:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121600_008"
down_revision: str | None = "202607121500_007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FEATURE_VALUES = (
    "finding",
    "recommendation",
    "executive_summary",
    "business_summary",
    "quick_win",
)
_FEATURE_IN = ", ".join(f"'{v}'" for v in _FEATURE_VALUES)
_STATUS_IN = ", ".join(
    f"'{s}'" for s in ("queued", "running", "completed", "failed", "cancelled")
)


def upgrade() -> None:
    op.create_table(
        "ai_generation_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_hash", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("worker", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"feature IN ({_FEATURE_IN})", name="ai_generation_jobs_feature_chk"
        ),
        sa.CheckConstraint(
            f"entity_type IN ({_FEATURE_IN})", name="ai_generation_jobs_entity_type_chk"
        ),
        sa.CheckConstraint(
            f"status IN ({_STATUS_IN})", name="ai_generation_jobs_status_chk"
        ),
        sa.CheckConstraint("attempt >= 0", name="ai_generation_jobs_attempt_chk"),
    )
    op.create_index(
        "ai_generation_jobs_status_idx", "ai_generation_jobs", ["status"]
    )
    op.create_index(
        "ai_generation_jobs_feature_entity_idx",
        "ai_generation_jobs",
        ["feature", "entity_id"],
    )
    op.create_index(
        "ai_generation_jobs_audit_idx", "ai_generation_jobs", ["audit_id"]
    )
    op.create_index(
        "ai_generation_jobs_created_idx", "ai_generation_jobs", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ai_generation_jobs_created_idx", table_name="ai_generation_jobs")
    op.drop_index("ai_generation_jobs_audit_idx", table_name="ai_generation_jobs")
    op.drop_index(
        "ai_generation_jobs_feature_entity_idx", table_name="ai_generation_jobs"
    )
    op.drop_index("ai_generation_jobs_status_idx", table_name="ai_generation_jobs")
    op.drop_table("ai_generation_jobs")
