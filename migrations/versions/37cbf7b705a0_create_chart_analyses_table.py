"""create_chart_analyses_table

Revision ID: 37cbf7b705a0
Revises: 40fb4096fd3f
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "37cbf7b705a0"
down_revision = "40fb4096fd3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chart_analyses",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("suggestion", sa.String(30), nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("confidence_label", sa.String(20), nullable=True),
        sa.Column("confidence_justification", sa.String(500), nullable=True),
        sa.Column("trend_direction", sa.String(20), nullable=True),
        sa.Column("trend_strength", sa.String(20), nullable=True),
        sa.Column("support_level", sa.Float, nullable=True),
        sa.Column("resistance_level", sa.Float, nullable=True),
        sa.Column("setup_description", sa.String(500), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("risks_json", sa.Text, nullable=True),
        sa.Column("bull_scenario", sa.Text, nullable=True),
        sa.Column("bear_scenario", sa.Text, nullable=True),
        sa.Column("raw_response", sa.Text, nullable=True),
        sa.Column("screenshot_path", sa.String(500), nullable=True),
    )
    op.create_index("ix_chart_analyses_session_id", "chart_analyses", ["session_id"])
    op.create_index("ix_chart_analyses_asset", "chart_analyses", ["asset"])
    op.create_index("ix_chart_analyses_created_at", "chart_analyses", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chart_analyses_created_at", "chart_analyses")
    op.drop_index("ix_chart_analyses_asset", "chart_analyses")
    op.drop_index("ix_chart_analyses_session_id", "chart_analyses")
    op.drop_table("chart_analyses")
