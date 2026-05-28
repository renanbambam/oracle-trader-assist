"""Market domain — entities."""

from datetime import datetime

from pydantic import Field

from oracle.domain.market.enums import AssetClass, MarketSession, Timeframe
from oracle.domain.market.value_objects import OHLCVBar, Ticker
from oracle.domain.shared.base import Entity


class MarketSnapshot(Entity):
    """Point-in-time state of an asset on a given timeframe.

    Captures everything required to perform analysis at a specific moment.
    Persisted as a reference for replay sessions and historical correlation.
    """

    symbol: str
    timeframe: Timeframe
    asset_class: AssetClass = AssetClass.STOCK
    session: MarketSession = MarketSession.REGULAR

    current_price: float = Field(gt=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    spread: float = Field(ge=0)

    current_bar: OHLCVBar
    recent_bars: list[OHLCVBar] = Field(default_factory=list)

    captured_at: datetime

    @property
    def bar_count(self) -> int:
        return len(self.recent_bars)

    @property
    def is_liquid(self) -> bool:
        """Spread < 0.5% of price is considered liquid enough for analysis."""
        if self.current_price == 0:
            return False
        return self.spread / self.current_price < 0.005
