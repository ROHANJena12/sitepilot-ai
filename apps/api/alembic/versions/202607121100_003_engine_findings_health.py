"""Create engine_executions, audit_findings, health_scores; expand audit_runs status CHECK.

Revision ID: 202607121100_003
Revises: 202607121000_002
Create Date: 2026-07-12 11:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121100_003"
down_revision: str | None = "202607121000_002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS_VALUES = (
    "pending",
    "validating",
    "crawling",
    "parsing",
    "seo",
    "accessibility",
    "security",
    "performance",
    "business",
    "health",
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

_ENGINE_NAMES = (
    "url_validation",
    "crawler",
    "parser",
    "html_parser",
    "seo",
    "seo_intelligence",
    "accessibility",
    "security",
    "performance",
    "business",
    "business_impact",
    "health",
    "health_score",
    "roi",
    "data_quality",
    "ai_recommendation",
    "report_builder",
    "pdf",
)
_ENGINE_CHK = ", ".join(f"'{n}'" for n in _ENGINE_NAMES)
_EXEC_STATUS_CHK = ", ".join(
    f"'{s}'" for s in ("pending", "running", "success", "partial", "failed", "skipped")
)
_SEVERITY_CHK = ", ".join(f"'{s}'" for s in ("critical", "high", "medium", "low", "info"))
_FINDING_STATUS_CHK = ", ".join(
    f"'{s}'" for s in ("pass", "fail", "warn", "info", "skip", "error")
)


def upgrade() -> None:
    op.drop_constraint("audit_runs_status_chk", "audit_runs", type_="check")
    op.create_check_constraint(
        "audit_runs_status_chk",
        "audit_runs",
        f"status IN ({_STATUS_CHK})",
    )

    op.create_table(
        "engine_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_name", sa.Text(), nullable=False),
        sa.Column("engine_version", sa.Text(), server_default=sa.text("'0.1.0'"), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("input_artifact_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"engine_name IN ({_ENGINE_CHK})", name="engine_executions_name_chk"),
        sa.CheckConstraint(f"status IN ({_EXEC_STATUS_CHK})", name="engine_executions_status_chk"),
        sa.CheckConstraint(
            "execution_time_ms IS NULL OR execution_time_ms >= 0",
            name="engine_executions_duration_chk",
        ),
        sa.UniqueConstraint(
            "audit_run_id",
            "engine_name",
            "attempt",
            name="engine_executions_run_engine_attempt_uidx",
        ),
    )
    op.create_index("engine_executions_run_idx", "engine_executions", ["audit_run_id"])
    op.create_index(
        "engine_executions_name_status_idx",
        "engine_executions",
        ["engine_name", "status"],
    )

    op.create_table(
        "audit_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("engine_name", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), server_default=sa.text("100"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'fail'"), nullable=False),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("technical_detail", sa.Text(), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("resolution_status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["engine_execution_id"],
            ["engine_executions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"severity IN ({_SEVERITY_CHK})", name="audit_findings_severity_chk"),
        sa.CheckConstraint(f"status IN ({_FINDING_STATUS_CHK})", name="audit_findings_status_chk"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="audit_findings_confidence_chk",
        ),
        sa.UniqueConstraint("audit_run_id", "finding_id", name="audit_findings_run_finding_uidx"),
    )
    op.create_index("audit_findings_run_idx", "audit_findings", ["audit_run_id"])
    op.create_index(
        "audit_findings_category_sev_idx",
        "audit_findings",
        ["category", "severity"],
    )
    op.create_index("audit_findings_engine_idx", "audit_findings", ["engine_name"])

    op.create_table(
        "health_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.SmallInteger(), nullable=False),
        sa.Column("seo_score", sa.SmallInteger(), nullable=True),
        sa.Column("accessibility_score", sa.SmallInteger(), nullable=True),
        sa.Column("security_score", sa.SmallInteger(), nullable=True),
        sa.Column("performance_score", sa.SmallInteger(), nullable=True),
        sa.Column("business_score", sa.SmallInteger(), nullable=True),
        sa.Column("grade", sa.Text(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=False),
        sa.Column(
            "category_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "penalties",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audit_run_id", name="health_scores_audit_run_uidx"),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="health_scores_overall_chk",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="health_scores_confidence_chk",
        ),
    )


def downgrade() -> None:
    op.drop_table("health_scores")
    op.drop_index("audit_findings_engine_idx", table_name="audit_findings")
    op.drop_index("audit_findings_category_sev_idx", table_name="audit_findings")
    op.drop_index("audit_findings_run_idx", table_name="audit_findings")
    op.drop_table("audit_findings")
    op.drop_index("engine_executions_name_status_idx", table_name="engine_executions")
    op.drop_index("engine_executions_run_idx", table_name="engine_executions")
    op.drop_table("engine_executions")

    legacy = (
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
    legacy_chk = ", ".join(f"'{s}'" for s in legacy)
    op.drop_constraint("audit_runs_status_chk", "audit_runs", type_="check")
    op.create_check_constraint(
        "audit_runs_status_chk",
        "audit_runs",
        f"status IN ({legacy_chk})",
    )
