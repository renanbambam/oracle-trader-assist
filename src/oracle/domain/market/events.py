"""Market domain — domain events."""

from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar, Ticker
from oracle.domain.shared.base import DomainEvent


class MarketTickerUpdated(DomainEvent):
    """Fired when a new live tick is received for a symbol.

    High-frequency event — consumer (WebSocket broadcaster) should
    throttle or debounce to avoid flooding clients.
    """

    event_type: str = "market.ticker_updated"
    ticker: Ticker


class CandleClosed(DomainEvent):
    """Fired when an OHLCV bar completes (timeframe closes).

    Triggers analysis refresh for clients subscribed to that symbol/timeframe.
    """

    event_type: str = "market.candle_closed"
    bar: OHLCVBar
    timeframe: Timeframe
