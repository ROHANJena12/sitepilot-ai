"""Add progress, timing, retry, and cancel_reason to ai_generation_jobs (Sprint 26.1).

Revision ID: 202607121700_009
Revises: 202607121600_008
Create Date: 2026-07-12 17:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607121700_009"
down_revision: str | None = "202607121600_008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANCEL_IN = ", ".join(
    f"'{r}'"
    for r in (
        "USER_REQUESTED",
        "TIMEOUT",
        "SHUTDOWN",
        "PROVIDER_FAILURE",
        "DUPLICATE",
        "SUPERSEDED",
    )
)


def upgrade() -> None:
    op.add_column(
        "ai_generation_jobs",
        sa.Column("progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column(
            "max_attempts", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column("cancel_reason", sa.Text(), nullable=True),
    )
    # Backfill queued_at from created_at for existing rows.
    op.execute(
        sa.text("UPDATE ai_generation_jobs SET queued_at = created_at WHERE queued_at IS NULL")
    )
    op.execute(
        sa.text("UPDATE ai_generation_jobs SET last_error = error WHERE last_error IS NULL")
    )
    op.create_check_constraint(
        "ai_generation_jobs_progress_chk",
        "ai_generation_jobs",
        "progress >= 0 AND progress <= 100",
    )
    op.create_check_constraint(
        "ai_generation_jobs_max_attempts_chk",
        "ai_generation_jobs",
        "max_attempts >= 1",
    )
    op.create_check_constraint(
        "ai_generation_jobs_cancel_reason_chk",
        "ai_generation_jobs",
        f"cancel_reason IS NULL OR cancel_reason IN ({_CANCEL_IN})",
    )
    op.create_index(
        "ai_generation_jobs_queued_idx", "ai_generation_jobs", ["queued_at"]
    )


def downgrade() -> None:
    op.drop_index("ai_generation_jobs_queued_idx", table_name="ai_generation_jobs")
    op.drop_constraint(
        "ai_generation_jobs_cancel_reason_chk",
        "ai_generation_jobs",
        type_="check",
    )
    op.drop_constraint(
        "ai_generation_jobs_max_attempts_chk",
        "ai_generation_jobs",
        type_="check",
    )
    op.drop_constraint(
        "ai_generation_jobs_progress_chk",
        "ai_generation_jobs",
        type_="check",
    )
    op.drop_column("ai_generation_jobs", "cancel_reason")
    op.drop_column("ai_generation_jobs", "next_retry_at")
    op.drop_column("ai_generation_jobs", "max_attempts")
    op.drop_column("ai_generation_jobs", "last_error")
    op.drop_column("ai_generation_jobs", "queued_at")
    op.drop_column("ai_generation_jobs", "progress")
