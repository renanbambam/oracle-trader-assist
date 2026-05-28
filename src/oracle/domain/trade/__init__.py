"""Trade bounded context — public API."""

from oracle.domain.trade.contracts import TradeRepository
from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus
from oracle.domain.trade.events import TradeClosed, TradeOpened
from oracle.domain.trade.value_objects import PriceLevel, RiskRatio

__all__ = [
    # Enums
    "Direction",
    "TradeStatus",
    "TradeResult",
    "EmotionalState",
    # Value Objects
    "RiskRatio",
    "PriceLevel",
    # Entities
    "Trade",
    # Contracts
    "TradeRepository",
    # Events
    "TradeOpened",
    "TradeClosed",
]
