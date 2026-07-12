"""Create ai_generations table (Sprint 24 — versioned AI artifacts).

Revision ID: 202607121500_007
Revises: 202607121400_006
Create Date: 2026-07-12 15:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607121500_007"
down_revision: str | None = "202607121400_006"
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


def upgrade() -> None:
    op.create_table(
        "ai_generations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("builder_version", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.Text(), nullable=True),
        sa.Column("report_hash", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=True),
        sa.Column("response_hash", sa.Text(), nullable=False),
        sa.Column("locale", sa.Text(), server_default=sa.text("'en'"), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("telemetry_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("diagnostics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'success'"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["audit_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "feature",
            "entity_id",
            "report_hash",
            "version",
            name="ai_generations_feature_entity_report_ver_uidx",
        ),
        sa.CheckConstraint(
            f"feature IN ({_FEATURE_IN})",
            name="ai_generations_feature_chk",
        ),
        sa.CheckConstraint(
            f"entity_type IN ({_FEATURE_IN})",
            name="ai_generations_entity_type_chk",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'cached', 'error')",
            name="ai_generations_status_chk",
        ),
        sa.CheckConstraint("version >= 1", name="ai_generations_version_chk"),
    )
    op.create_index("ai_generations_audit_idx", "ai_generations", ["audit_id"])
    op.create_index("ai_generations_feature_idx", "ai_generations", ["feature"])
    op.create_index(
        "ai_generations_entity_idx", "ai_generations", ["entity_type", "entity_id"]
    )
    op.create_index(
        "ai_generations_report_hash_idx", "ai_generations", ["report_hash"]
    )
    op.create_index(
        "ai_generations_generation_id_idx", "ai_generations", ["generation_id"]
    )
    op.create_index(
        "ai_generations_response_hash_idx", "ai_generations", ["response_hash"]
    )


def downgrade() -> None:
    op.drop_index("ai_generations_response_hash_idx", table_name="ai_generations")
    op.drop_index("ai_generations_generation_id_idx", table_name="ai_generations")
    op.drop_index("ai_generations_report_hash_idx", table_name="ai_generations")
    op.drop_index("ai_generations_entity_idx", table_name="ai_generations")
    op.drop_index("ai_generations_feature_idx", table_name="ai_generations")
    op.drop_index("ai_generations_audit_idx", table_name="ai_generations")
    op.drop_table("ai_generations")
