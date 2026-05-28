"""SQLAlchemy ORM models for the memory bounded context.

Two tables:
  context_sessions — active multi-turn conversation windows per asset.
  memory_records   — persisted knowledge extracted from past sessions.

ChatMessage turns are stored as JSON in context_sessions.turns_json
to avoid a separate table for this phase.
"""

import uuid

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.infrastructure.database.base import Base


class ContextSessionOrm(Base):
    __tablename__ = "context_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turns_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    trim_strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="oldest_first")
    started_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    last_active_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_context_sessions_asset_status", "asset", "status"),
        Index("ix_context_sessions_last_active_at", "last_active_at"),
    )


class MemoryRecordOrm(Base):
    __tablename__ = "memory_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    setup_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_analysis_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_trade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_memory_records_asset_setup", "asset", "setup_type"),
    )
