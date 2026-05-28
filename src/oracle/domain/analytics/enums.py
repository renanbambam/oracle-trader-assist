"""Analytics domain — enumerations."""

from enum import StrEnum


class MetricPeriod(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ALL_TIME = "all_time"


class SetupCategory(StrEnum):
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    TREND_CONTINUATION = "trend_continuation"
    RANGE = "range"
    NEWS_DRIVEN = "news_driven"
    CUSTOM = "custom"


class PerformanceGrade(StrEnum):
    """Letter grade assigned to a performance period.

    Derived from win rate + expected value combination.
    A = consistent profitability; F = systematic issues to address.
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
