"""Briefing application — input/output DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field


class GenerateBriefingInput(BaseModel):
    assets: list[str] = Field(min_length=1)
    include_economic_calendar: bool = True
    include_recent_trades: bool = True
    max_assets: int = Field(default=5, ge=1, le=10)


class BriefingOutput(BaseModel):
    content: str
    assets_covered: list[str]
    key_levels: dict[str, dict[str, float]]
    upcoming_events: list[dict]
    recent_trade_context: str
    generated_at: datetime
