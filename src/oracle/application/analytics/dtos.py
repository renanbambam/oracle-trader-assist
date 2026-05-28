"""Analytics application — input/output DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from oracle.domain.analytics.enums import MetricPeriod, PerformanceGrade


class PerformanceQuery(BaseModel):
    period: MetricPeriod = MetricPeriod.MONTHLY
    asset: str | None = None


class PerformanceOutput(BaseModel):
    period: MetricPeriod
    period_start: datetime
    period_end: datetime
    win_rate_pct: float
    total_trades: int
    total_r: float
    average_r: float
    expected_value_r: float
    max_drawdown_r: float
    grade: PerformanceGrade
    generated_at: datetime


class SetupStatsQuery(BaseModel):
    setup_category: str | None = None
    asset: str | None = None
    period: MetricPeriod = MetricPeriod.ALL_TIME
