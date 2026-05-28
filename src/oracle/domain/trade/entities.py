"""Trade domain — entities."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from oracle.domain.market.enums import Timeframe
from oracle.domain.shared.base import Entity
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus
from oracle.domain.trade.value_objects import RiskRatio


class Trade(Entity):
    """A single trading operation — from intent to final result.

    The core business entity. Every operation gets recorded here regardless
    of outcome. Data integrity is non-negotiable — no deletions allowed.

    Level validation enforces correct LONG/SHORT geometry on construction.
    This prevents invalid trades from ever entering the system.
    """

    asset: str
    direction: Direction
    timeframe: Timeframe
    status: TradeStatus = TradeStatus.OPEN

    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    exit: float | None = None

    result: TradeResult | None = None
    r_realized: float | None = None

    setup: str
    emotional_state: EmotionalState
    confidence_score: float | None = Field(default=None, ge=0.0, le=100.0)
    analysis_id: UUID | None = None

    notes: str | None = None
    reflection: str | None = None

    opened_at: datetime
    closed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_price_geometry(self) -> "Trade":
        if self.direction == Direction.LONG:
            if self.stop >= self.entry:
                raise ValueError("LONG: stop must be below entry")
            if self.target <= self.entry:
                raise ValueError("LONG: target must be above entry")
        else:
            if self.stop <= self.entry:
                raise ValueError("SHORT: stop must be above entry")
            if self.target >= self.entry:
                raise ValueError("SHORT: target must be below entry")
        return self

    @property
    def risk_ratio(self) -> RiskRatio:
        return RiskRatio.from_levels(self.entry, self.stop, self.target)

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.OPEN

    @property
    def is_emotionally_compromised(self) -> bool:
        """True for FOMO/REVANCHE — triggers AntiFOMOFilter warning."""
        return self.emotional_state in (EmotionalState.FOMO, EmotionalState.REVANCHE)
