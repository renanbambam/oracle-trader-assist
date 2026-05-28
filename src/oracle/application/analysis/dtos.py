"""Analysis application — input/output DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from oracle.domain.analysis.enums import ConfidenceLabel, Suggestion, TrendDirection
from oracle.domain.market.enums import Timeframe


class RunAnalysisInput(BaseModel):
    asset: str
    timeframe: Timeframe
    screenshot_b64: str | None = None
    session_id: UUID | None = None
    notes: str | None = None


class RunAnalysisOutput(BaseModel):
    analysis_id: UUID
    asset: str
    timeframe: Timeframe
    suggestion: Suggestion
    confidence_score: float
    confidence_label: ConfidenceLabel
    trend_direction: TrendDirection
    reasoning: str
    risks: list[str]
    bull_scenario: str
    bear_scenario: str
    created_at: datetime


class SendMessageInput(BaseModel):
    session_id: UUID
    content: str


class ScoreSetupInput(BaseModel):
    trend_alignment: float = Field(ge=0.0, le=1.0)
    setup_quality: float = Field(ge=0.0, le=1.0)
    historical_match: float = Field(ge=0.0, le=1.0)
    macro_context: float = Field(ge=0.0, le=1.0)
    market_quality: float = Field(ge=0.0, le=1.0)
    emotional_state: float = Field(ge=0.0, le=1.0)


class ScoreSetupOutput(BaseModel):
    score: float
    label: ConfidenceLabel
    justification: str
    weighted_breakdown: dict[str, float]
