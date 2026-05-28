"""Replay domain — value objects."""

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from oracle.domain.shared.base import ValueObject


class TimeRange(ValueObject):
    """Closed datetime interval defining a replay session's scope."""

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_range(self) -> "TimeRange":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    @property
    def duration_days(self) -> float:
        return self.duration_hours / 24


class FrameAnnotation(ValueObject):
    """Visual annotation pinned to a specific replay frame.

    Annotations are overlaid on the chart during replay playback.
    The color field accepts any CSS hex color string.
    """

    type: str  # "trade_opened" | "trade_closed" | "ai_marker" | "news_event" | "custom"
    label: str
    color: str = "#FFD700"
    metadata: dict[str, Any] = Field(default_factory=dict)
