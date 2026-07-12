"""Add phase_history + failure_category to ai_generation_jobs (Sprint 26.2).

Revision ID: 202607121800_010
Revises: 202607121700_009
Create Date: 2026-07-12 18:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121800_010"
down_revision: str | None = "202607121700_009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FAILURE_IN = ", ".join(
    f"'{c}'"
    for c in (
        "UNKNOWN",
        "VALIDATION",
        "GROUNDING",
        "PROVIDER",
        "TIMEOUT",
        "PERSISTENCE",
        "QUEUE",
        "USER_CANCELLED",
        "INTERNAL",
    )
)


def upgrade() -> None:
    op.add_column(
        "ai_generation_jobs",
        sa.Column(
            "phase_history",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_generation_jobs",
        sa.Column("failure_category", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ai_generation_jobs_failure_category_chk",
        "ai_generation_jobs",
        f"failure_category IS NULL OR failure_category IN ({_FAILURE_IN})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ai_generation_jobs_failure_category_chk",
        "ai_generation_jobs",
        type_="check",
    )
    op.drop_column("ai_generation_jobs", "failure_category")
    op.drop_column("ai_generation_jobs", "phase_history")
