"""create_memory_tables

Revision ID: b9f1a2e3c4d5
Revises: 37cbf7b705a0
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "b9f1a2e3c4d5"
down_revision = "37cbf7b705a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("turns_json", sa.Text, nullable=True),
        sa.Column("trim_strategy", sa.String(20), nullable=False, server_default="oldest_first"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_sessions_asset_status", "context_sessions", ["asset", "status"])
    op.create_index("ix_context_sessions_last_active_at", "context_sessions", ["last_active_at"])

    op.create_table(
        "memory_records",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("setup_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_analysis_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_trade_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=True),
    )
    op.create_index("ix_memory_records_asset_setup", "memory_records", ["asset", "setup_type"])


def downgrade() -> None:
    op.drop_table("memory_records")
    op.drop_table("context_sessions")
