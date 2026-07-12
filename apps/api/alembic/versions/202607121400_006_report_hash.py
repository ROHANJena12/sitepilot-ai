"""Add reports.report_hash for content-addressed regeneration (Sprint 16.1).

Revision ID: 202607121400_006
Revises: 202607121300_005
Create Date: 2026-07-12 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607121400_006"
down_revision: str | None = "202607121300_005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("report_hash", sa.Text(), nullable=True))
    op.create_index("reports_hash_idx", "reports", ["report_hash"])


def downgrade() -> None:
    op.drop_index("reports_hash_idx", table_name="reports")
    op.drop_column("reports", "report_hash")
