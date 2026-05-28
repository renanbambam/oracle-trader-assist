"""SQLAlchemy ORM model for computed performance reports."""

import uuid

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from oracle.infrastructure.database.base import Base


class PerformanceReportOrm(Base):
    __tablename__ = "performance_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    period: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    asset: Mapped[str | None] = mapped_column(String(20), nullable=True)

    win_rate_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_r: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_r: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_value_r: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_drawdown_r: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grade: Mapped[str] = mapped_column(String(5), nullable=False, default="F")
    generated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_performance_reports_period", "period"),
        Index("ix_performance_reports_generated_at", "generated_at"),
    )
