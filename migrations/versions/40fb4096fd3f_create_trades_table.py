"""create_trades_table

Revision ID: 40fb4096fd3f
Revises:
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa

revision = "40fb4096fd3f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("entry", sa.Float, nullable=False),
        sa.Column("stop", sa.Float, nullable=False),
        sa.Column("target", sa.Float, nullable=False),
        sa.Column("exit", sa.Float, nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("r_realized", sa.Float, nullable=True),
        sa.Column("setup", sa.String(100), nullable=False),
        sa.Column("emotional_state", sa.String(20), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("analysis_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("reflection", sa.String(2000), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_trades_asset", "trades", ["asset"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])


def downgrade() -> None:
    op.drop_index("ix_trades_opened_at", "trades")
    op.drop_index("ix_trades_status", "trades")
    op.drop_index("ix_trades_asset", "trades")
    op.drop_table("trades")
