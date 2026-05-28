"""create_replay_sessions_table

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "replay_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(5), nullable=False),
        sa.Column("range_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("range_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("speed", sa.String(5), nullable=False, server_default="1x"),
        sa.Column("current_frame", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_frames", sa.Integer, nullable=False, server_default="0"),
        sa.Column("frames_json", sa.Text, nullable=True),
    )
    op.create_index("ix_replay_sessions_asset", "replay_sessions", ["asset"])
    op.create_index("ix_replay_sessions_state", "replay_sessions", ["state"])


def downgrade() -> None:
    op.drop_table("replay_sessions")
