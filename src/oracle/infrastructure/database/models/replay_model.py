"""SQLAlchemy ORM model for replay sessions.

Frames are stored as JSON in frames_json — acceptable for MVP since a
full trading day of M5 bars is ~100 frames (~100KB of JSON).
"""

import uuid

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.infrastructure.database.base import Base


class ReplaySessionOrm(Base):
    __tablename__ = "replay_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    range_start: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    range_end: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="idle")
    speed: Mapped[str] = mapped_column(String(5), nullable=False, default="1x")
    current_frame: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_frames: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    frames_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_replay_sessions_asset", "asset"),
        Index("ix_replay_sessions_state", "state"),
    )
