"""Create audit_runs (DATABASE_SPEC §9 + Sprint 3 progress columns).

Revision ID: 202607121000_002
Revises: 202607120900_001
Create Date: 2026-07-12 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121000_002"
down_revision: str | None = "202607120900_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_VALUES = (
    "pending",
    "validating",
    "crawling",
    "analyzing",
    "scoring",
    "enriching",
    "building_report",
    "complete",
    "complete_with_warnings",
    "failed",
    "cancelled",
)
_STATUS_CHK = ", ".join(f"'{s}'" for s in _STATUS_VALUES)


def upgrade() -> None:
    op.create_table(
        "audit_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("current_engine", sa.Text(), nullable=True),
        sa.Column("progress_percent", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("failure_code", sa.Text(), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("health_score", sa.SmallInteger(), nullable=True),
        sa.Column("seo_score", sa.SmallInteger(), nullable=True),
        sa.Column("performance_score", sa.SmallInteger(), nullable=True),
        sa.Column("security_score", sa.SmallInteger(), nullable=True),
        sa.Column("accessibility_score", sa.SmallInteger(), nullable=True),
        sa.Column("business_score", sa.SmallInteger(), nullable=True),
        sa.Column("roi_score", sa.SmallInteger(), nullable=True),
        sa.Column("confidence_score", sa.SmallInteger(), nullable=True),
        sa.Column("scoring_config_version", sa.Text(), nullable=True),
        sa.Column(
            "engine_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("client_ip_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"status IN ({_STATUS_CHK})", name="audit_runs_status_chk"),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="audit_runs_progress_chk",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="audit_runs_duration_chk",
        ),
        sa.CheckConstraint(
            "health_score IS NULL OR (health_score BETWEEN 0 AND 100)",
            name="audit_runs_health_score_chk",
        ),
        sa.CheckConstraint(
            "seo_score IS NULL OR (seo_score BETWEEN 0 AND 100)",
            name="audit_runs_seo_score_chk",
        ),
        sa.CheckConstraint(
            "performance_score IS NULL OR (performance_score BETWEEN 0 AND 100)",
            name="audit_runs_performance_score_chk",
        ),
        sa.CheckConstraint(
            "security_score IS NULL OR (security_score BETWEEN 0 AND 100)",
            name="audit_runs_security_score_chk",
        ),
        sa.CheckConstraint(
            "accessibility_score IS NULL OR (accessibility_score BETWEEN 0 AND 100)",
            name="audit_runs_accessibility_score_chk",
        ),
        sa.CheckConstraint(
            "business_score IS NULL OR (business_score BETWEEN 0 AND 100)",
            name="audit_runs_business_score_chk",
        ),
        sa.CheckConstraint(
            "roi_score IS NULL OR (roi_score BETWEEN 0 AND 100)",
            name="audit_runs_roi_score_chk",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score BETWEEN 0 AND 100)",
            name="audit_runs_confidence_score_chk",
        ),
        sa.ForeignKeyConstraint(["website_id"], ["websites.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "audit_runs_website_created_idx",
        "audit_runs",
        ["website_id", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "audit_runs_org_status_idx",
        "audit_runs",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_index(
        "audit_runs_status_idx",
        "audit_runs",
        ["status"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("audit_runs_status_idx", table_name="audit_runs")
    op.drop_index("audit_runs_org_status_idx", table_name="audit_runs")
    op.drop_index("audit_runs_website_created_idx", table_name="audit_runs")
    op.drop_table("audit_runs")
