"""Analytics domain — entities."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field

from oracle.domain.analytics.enums import MetricPeriod, PerformanceGrade, SetupCategory
from oracle.domain.analytics.value_objects import DrawdownMetric, ExpectedValue, WinRate
from oracle.domain.shared.base import Entity


class SetupStats(Entity):
    """Performance statistics for a specific trade setup type and period.

    Computed on demand from trade history — never manually updated.
    """

    setup_category: SetupCategory
    asset: str | None = None
    period: MetricPeriod

    win_rate: WinRate
    expected_value: ExpectedValue
    total_trades: int = Field(ge=0)
    average_hold_minutes: float | None = None
    best_timeframes: list[str] = Field(default_factory=list)

    period_start: datetime
    period_end: datetime


class PerformanceReport(Entity):
    """Aggregated performance over a defined period.

    Always recalculated from raw trade data — never mutated.
    The grade field summarizes performance for quick reference.
    """

    period: MetricPeriod
    period_start: datetime
    period_end: datetime

    win_rate: WinRate
    expected_value: ExpectedValue
    drawdown: DrawdownMetric

    total_r: float
    average_r_per_trade: float
    best_trade_r: float
    worst_trade_r: float
    total_trades: int = Field(ge=0)

    grade: PerformanceGrade
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TraderProfile(Entity):
    """Behavioral and performance profile of the trader.

    Evolves as trade data accumulates. Used to personalize analysis
    risk management defaults and setup prioritization.
    """

    display_name: str
    preferred_assets: list[str] = Field(default_factory=list)
    preferred_timeframes: list[str] = Field(default_factory=list)
    preferred_setups: list[SetupCategory] = Field(default_factory=list)

    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=100)
    max_daily_risk_pct: float = Field(default=3.0, gt=0, le=100)

    all_time_stats: PerformanceReport | None = None
    emotional_pattern: dict[str, float] = Field(default_factory=dict)
