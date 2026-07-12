"""Create reports table (DATABASE_SPEC §16).

Revision ID: 202607121300_005
Revises: 202607121200_004
Create Date: 2026-07-12 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121300_005"
down_revision: str | None = "202607121200_004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'ready'"), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column(
            "business_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("report_json_uri", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("pdf_content_hash", sa.Text(), nullable=True),
        sa.Column("pdf_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "charts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.Text(), server_default=sa.text("'report.v1'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_run_id", name="reports_audit_run_uidx"),
        sa.CheckConstraint(
            "status IN ('ready', 'generating_pdf', 'failed')",
            name="reports_status_chk",
        ),
        sa.CheckConstraint("version >= 1", name="reports_version_chk"),
    )
    op.create_index(
        "reports_json_gin",
        "reports",
        ["report_json"],
        postgresql_using="gin",
        postgresql_ops={"report_json": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_index("reports_json_gin", table_name="reports")
    op.drop_table("reports")
