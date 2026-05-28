"""create_performance_reports_table

Revision ID: c2d3e4f5a6b7
Revises: b9f1a2e3c4d5
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b9f1a2e3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "performance_reports",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=True),
        sa.Column("win_rate_pct", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_r", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("average_r", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("expected_value_r", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("max_drawdown_r", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("grade", sa.String(5), nullable=False, server_default="F"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_performance_reports_period", "performance_reports", ["period"])
    op.create_index("ix_performance_reports_generated_at", "performance_reports", ["generated_at"])


def downgrade() -> None:
    op.drop_table("performance_reports")
