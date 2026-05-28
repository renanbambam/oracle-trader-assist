"""Market domain — contracts (protocols/interfaces).

These are the ports for market data. Implementations live in
infrastructure/market_data/ (MT5Adapter, MockAdapter).
"""

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from oracle.domain.market.entities import MarketSnapshot
from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar, Ticker


class NewsItem:
    """Plain data holder for a news article."""
    __slots__ = ("title", "summary", "source", "published_at")

    def __init__(self, title: str, summary: str, source: str, published_at: str) -> None:
        self.title = title
        self.summary = summary
        self.source = source
        self.published_at = published_at


class CalendarEvent:
    """Plain data holder for an economic calendar event."""
    __slots__ = ("time", "title", "impact", "country", "actual", "forecast", "previous")

    def __init__(
        self,
        time: str,
        title: str,
        impact: str,
        country: str,
        actual: str = "",
        forecast: str = "",
        previous: str = "",
    ) -> None:
        self.time = time
        self.title = title
        self.impact = impact
        self.country = country
        self.actual = actual
        self.forecast = forecast
        self.previous = previous


@runtime_checkable
class NewsProvider(Protocol):
    """Port for fetching financial news by asset keyword."""

    async def get_news(self, asset: str, max_results: int = 5) -> list[NewsItem]: ...


@runtime_checkable
class CalendarProvider(Protocol):
    """Port for fetching today's economic calendar events."""

    async def get_today_events(self) -> list[CalendarEvent]: ...


@runtime_checkable
class MarketDataProvider(Protocol):
    """Port for fetching live and historical market data.

    Implemented by MT5Adapter (Windows production) and MockAdapter
    (tests, non-Windows, and offline development).
    """

    async def get_snapshot(self, symbol: str, timeframe: Timeframe) -> MarketSnapshot: ...

    async def get_historical(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int,
    ) -> list[OHLCVBar]: ...

    async def get_price(self, symbol: str) -> float: ...

    async def is_market_open(self, symbol: str) -> bool: ...

    def stream_ticks(self, symbol: str) -> AsyncGenerator[Ticker, None]: ...
