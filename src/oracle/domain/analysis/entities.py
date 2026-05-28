"""Analysis domain — entities."""

from uuid import UUID

from pydantic import Field

from oracle.domain.analysis.enums import (
    AnalysisStatus,
    ConfidenceLabel,
    Suggestion,
    TrendDirection,
    TrendStrength,
)
from oracle.domain.analysis.value_objects import ConfidenceScore
from oracle.domain.market.enums import Timeframe
from oracle.domain.shared.base import Entity


class ChartAnalysis(Entity):
    """Result of a full AI-powered chart analysis.

    Core artifact of Oracle — persisted and referenced by trades,
    replays and analytics. Created in PENDING status, transitions to
    COMPLETED once the AI response is parsed and persisted.
    """

    session_id: UUID
    asset: str
    timeframe: Timeframe
    status: AnalysisStatus = AnalysisStatus.PENDING

    # Populated after AI completion
    suggestion: Suggestion | None = None
    confidence: ConfidenceScore | None = None
    trend_direction: TrendDirection | None = None
    trend_strength: TrendStrength | None = None

    support_level: float | None = None
    resistance_level: float | None = None
    setup_description: str | None = None
    reasoning: str | None = None
    risks: list[str] = Field(default_factory=list)
    bull_scenario: str | None = None
    bear_scenario: str | None = None

    raw_response: str | None = None
    screenshot_path: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.status == AnalysisStatus.COMPLETED

    @property
    def is_actionable(self) -> bool:
        return self.suggestion == Suggestion.OPERAR

    @property
    def is_high_conviction(self) -> bool:
        if self.confidence is None:
            return False
        return self.confidence.label in (ConfidenceLabel.ALTA, ConfidenceLabel.MUITO_ALTA)


class AIResponse(Entity):
    """Record of a single Claude API call for cost and latency tracking.

    Each analysis or chat message creates one AIResponse. The
    cached_tokens field is critical — it measures prompt caching ROI.
    """

    session_id: UUID
    model: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    content: str = ""
    is_streaming: bool = False
    stream_ended: bool = False
    latency_ms: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def effective_tokens(self) -> int:
        """Tokens actually billed (excludes cached prompt tokens)."""
        return self.total_tokens - self.cached_tokens

    @property
    def cache_hit_ratio(self) -> float:
        if self.prompt_tokens == 0:
            return 0.0
        return round(self.cached_tokens / self.prompt_tokens, 3)
