"""Create recommendations + recommendation_sources; add recommendation engine name/status.

Revision ID: 202607121200_004
Revises: 202607121100_003
Create Date: 2026-07-12 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121200_004"
down_revision: str | None = "202607121100_003"
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
    "recommendation",
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
    "recommendation",
    "roi",
    "data_quality",
    "ai_recommendation",
    "report_builder",
    "pdf",
)
_ENGINE_CHK = ", ".join(f"'{n}'" for n in _ENGINE_NAMES)

_PRIORITY_CHK = ", ".join(f"'{p}'" for p in ("Critical", "High", "Medium", "Low"))
_EFFORT_CHK = ", ".join(
    f"'{e}'" for e in ("Very Low", "Low", "Medium", "High", "Very High")
)
_IMPACT_CHK = ", ".join(f"'{i}'" for i in ("Critical", "High", "Medium", "Low"))
_REC_STATUS_CHK = ", ".join(
    f"'{s}'" for s in ("open", "accepted", "in_progress", "done", "dismissed")
)


def upgrade() -> None:
    op.drop_constraint("audit_runs_status_chk", "audit_runs", type_="check")
    op.create_check_constraint(
        "audit_runs_status_chk",
        "audit_runs",
        f"status IN ({_STATUS_CHK})",
    )

    op.drop_constraint("engine_executions_name_chk", "engine_executions", type_="check")
    op.create_check_constraint(
        "engine_executions_name_chk",
        "engine_executions",
        f"engine_name IN ({_ENGINE_CHK})",
    )

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommendation_id", sa.Text(), nullable=False),
        sa.Column("finding_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("technical_reason", sa.Text(), nullable=True),
        sa.Column("business_explanation", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("priority", sa.Text(), nullable=False),
        sa.Column("estimated_effort", sa.Text(), nullable=False),
        sa.Column("estimated_impact", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("is_quick_win", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "affected_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "related_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("model_used", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["engine_execution_id"],
            ["engine_executions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"priority IN ({_PRIORITY_CHK})", name="recommendations_priority_chk"),
        sa.CheckConstraint(f"estimated_effort IN ({_EFFORT_CHK})", name="recommendations_effort_chk"),
        sa.CheckConstraint(f"estimated_impact IN ({_IMPACT_CHK})", name="recommendations_impact_chk"),
        sa.CheckConstraint(f"status IN ({_REC_STATUS_CHK})", name="recommendations_status_chk"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="recommendations_confidence_chk",
        ),
        sa.UniqueConstraint(
            "audit_run_id",
            "recommendation_id",
            "version",
            name="recommendations_run_rec_ver_uidx",
        ),
    )
    op.create_index("recommendations_run_idx", "recommendations", ["audit_run_id"])
    op.create_index(
        "recommendations_priority_idx",
        "recommendations",
        ["audit_run_id", "priority"],
    )

    op.create_table(
        "recommendation_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("audit_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_row_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", sa.Text(), nullable=False),
        sa.Column("source_engine", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["recommendation_row_id"],
            ["recommendations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recommendation_row_id",
            "finding_id",
            name="recommendation_sources_row_finding_uidx",
        ),
    )
    op.create_index(
        "recommendation_sources_run_idx",
        "recommendation_sources",
        ["audit_run_id"],
    )
    op.create_index(
        "recommendation_sources_finding_idx",
        "recommendation_sources",
        ["finding_id"],
    )


def downgrade() -> None:
    op.drop_index("recommendation_sources_finding_idx", table_name="recommendation_sources")
    op.drop_index("recommendation_sources_run_idx", table_name="recommendation_sources")
    op.drop_table("recommendation_sources")
    op.drop_index("recommendations_priority_idx", table_name="recommendations")
    op.drop_index("recommendations_run_idx", table_name="recommendations")
    op.drop_table("recommendations")

    legacy_engines = (
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
    engine_chk = ", ".join(f"'{n}'" for n in legacy_engines)
    op.drop_constraint("engine_executions_name_chk", "engine_executions", type_="check")
    op.create_check_constraint(
        "engine_executions_name_chk",
        "engine_executions",
        f"engine_name IN ({engine_chk})",
    )

    legacy_status = (
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
    status_chk = ", ".join(f"'{s}'" for s in legacy_status)
    op.drop_constraint("audit_runs_status_chk", "audit_runs", type_="check")
    op.create_check_constraint(
        "audit_runs_status_chk",
        "audit_runs",
        f"status IN ({status_chk})",
    )
