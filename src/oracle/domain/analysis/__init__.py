"""Analysis bounded context — public API."""

from oracle.domain.analysis.contracts import AIProvider, AnalysisRepository
from oracle.domain.analysis.entities import AIResponse, ChartAnalysis
from oracle.domain.analysis.enums import (
    AnalysisStatus,
    ConfidenceLabel,
    Suggestion,
    TrendDirection,
    TrendStrength,
)
from oracle.domain.analysis.events import (
    AIStreamEnded,
    AIStreamToken,
    AnalysisCompleted,
    AnalysisRequested,
    ConfidenceUpdated,
)
from oracle.domain.analysis.value_objects import ConfidenceFactors, ConfidenceScore

__all__ = [
    # Enums
    "Suggestion",
    "ConfidenceLabel",
    "TrendDirection",
    "TrendStrength",
    "AnalysisStatus",
    # Value Objects
    "ConfidenceScore",
    "ConfidenceFactors",
    # Entities
    "ChartAnalysis",
    "AIResponse",
    # Contracts
    "AIProvider",
    "AnalysisRepository",
    # Events
    "AnalysisRequested",
    "AnalysisCompleted",
    "ConfidenceUpdated",
    "AIStreamToken",
    "AIStreamEnded",
]
