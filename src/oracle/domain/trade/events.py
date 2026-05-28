"""Trade domain — domain events."""

from uuid import UUID

from oracle.domain.shared.base import DomainEvent
from oracle.domain.trade.enums import Direction, TradeResult


class TradeOpened(DomainEvent):
    """Fired immediately after a trade is recorded as open."""

    event_type: str = "trade.opened"
    trade_id: UUID
    asset: str
    direction: Direction
    entry: float
    stop: float
    target: float
    setup: str


class TradeClosed(DomainEvent):
    """Fired when a trade result is recorded and the trade is closed."""

    event_type: str = "trade.closed"
    trade_id: UUID
    asset: str
    direction: Direction
    result: TradeResult
    r_realized: float
    exit_price: float
