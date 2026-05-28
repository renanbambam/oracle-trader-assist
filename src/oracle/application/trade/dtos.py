"""Trade application — input/output DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from oracle.domain.market.enums import Timeframe
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus


class RecordTradeInput(BaseModel):
    asset: str
    direction: Direction
    timeframe: Timeframe
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    setup: str
    emotional_state: EmotionalState
    analysis_id: UUID | None = None
    notes: str | None = None


class CloseTradeInput(BaseModel):
    trade_id: UUID
    exit_price: float = Field(gt=0)
    result: TradeResult
    notes: str | None = None


class TradeOutput(BaseModel):
    id: UUID
    asset: str
    direction: Direction
    timeframe: Timeframe
    status: TradeStatus
    entry: float
    stop: float
    target: float
    exit: float | None
    result: TradeResult | None
    r_realized: float | None
    rr_ratio: float
    setup: str
    emotional_state: EmotionalState
    confidence_score: float | None
    created_at: datetime
    closed_at: datetime | None


class ReflectionOutput(BaseModel):
    trade_id: UUID
    reflection: str
    memory_record_id: UUID


class ChecklistInput(BaseModel):
    asset: str
    direction: Direction
    timeframe: Timeframe
    setup: str
    emotional_state: EmotionalState
    rr_ratio: float = Field(gt=0)
    today_losses: int = Field(default=0, ge=0)


class ChecklistItemOutput(BaseModel):
    rule: str
    passed: bool
    blocking: bool
    message: str


class ChecklistOutput(BaseModel):
    items: list[ChecklistItemOutput]
    passed_count: int
    total_count: int
    verdict: str  # OPERAR | ATENÇÃO | NAO_OPERAR
