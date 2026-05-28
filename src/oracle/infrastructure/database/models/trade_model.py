"""SQLAlchemy ORM model for trades — no business logic, pure persistence mapping."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.infrastructure.database.base import Base


class TradeOrm(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    asset: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    entry: Mapped[float] = mapped_column(Float, nullable=False)
    stop: Mapped[float] = mapped_column(Float, nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    exit: Mapped[float | None] = mapped_column(Float, nullable=True)

    result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    r_realized: Mapped[float | None] = mapped_column(Float, nullable=True)

    setup: Mapped[str] = mapped_column(String(100), nullable=False)
    emotional_state: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reflection: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_trades_status", "status"),
        Index("ix_trades_opened_at", "opened_at"),
    )
