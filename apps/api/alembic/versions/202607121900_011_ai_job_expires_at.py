"""Add expires_at to ai_generation_jobs (Sprint 26.3).

Revision ID: 202607121900_011
Revises: 202607121800_010
Create Date: 2026-07-12 19:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607121900_011"
down_revision: str | None = "202607121800_010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_generation_jobs",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill completed jobs: completed_at + 24 hours.
    op.execute(
        sa.text(
            """
            UPDATE ai_generation_jobs
            SET expires_at = completed_at + INTERVAL '24 hours'
            WHERE status = 'completed' AND completed_at IS NOT NULL AND expires_at IS NULL
            """
        )
    )
    op.create_index(
        "ai_generation_jobs_expires_idx",
        "ai_generation_jobs",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ai_generation_jobs_expires_idx", table_name="ai_generation_jobs")
    op.drop_column("ai_generation_jobs", "expires_at")
