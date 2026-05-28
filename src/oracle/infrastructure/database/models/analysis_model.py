"""SQLAlchemy ORM model for chart analyses — no business logic."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.infrastructure.database.base import Base


class ChartAnalysisOrm(Base):
    __tablename__ = "chart_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    asset: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    suggestion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_justification: Mapped[str | None] = mapped_column(String(500), nullable=True)

    trend_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trend_strength: Mapped[str | None] = mapped_column(String(20), nullable=True)
    support_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    resistance_level: Mapped[float | None] = mapped_column(Float, nullable=True)

    setup_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    bull_scenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    bear_scenario: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (Index("ix_chart_analyses_created_at", "created_at"),)
