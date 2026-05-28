"""Analysis domain — domain events."""

from uuid import UUID

from oracle.domain.analysis.enums import ConfidenceLabel, Suggestion, TrendDirection
from oracle.domain.market.enums import Timeframe
from oracle.domain.shared.base import DomainEvent


class AnalysisRequested(DomainEvent):
    """Fired when a user submits a chart analysis request."""

    event_type: str = "analysis.requested"
    asset: str
    timeframe: Timeframe
    has_screenshot: bool = False


class AnalysisCompleted(DomainEvent):
    """Fired when AI analysis is fully processed and persisted.

    Payload carries the key fields so WebSocket clients can render
    the result without a follow-up REST call.
    """

    event_type: str = "analysis.completed"
    analysis_id: UUID
    asset: str
    timeframe: Timeframe
    suggestion: Suggestion
    confidence_score: float
    confidence_label: ConfidenceLabel
    trend_direction: TrendDirection


class ConfidenceUpdated(DomainEvent):
    """Fired when confidence score changes within an active session."""

    event_type: str = "analysis.confidence_updated"
    analysis_id: UUID
    old_score: float
    new_score: float
    new_label: ConfidenceLabel


class AIStreamToken(DomainEvent):
    """Fired for each token during a streaming AI response.

    Routed to the ai_stream WebSocket channel. is_final=True signals
    end-of-response so clients can stop the loading indicator.
    """

    event_type: str = "ai.stream_token"
    token: str
    is_final: bool = False


class AIStreamEnded(DomainEvent):
    """Fired when a streaming AI response completes."""

    event_type: str = "ai.stream_ended"
    response_id: UUID
    total_tokens: int
