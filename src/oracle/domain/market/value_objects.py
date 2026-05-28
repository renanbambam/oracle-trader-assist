"""Market domain — value objects (immutable market data structures)."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from oracle.domain.market.enums import MarketSession, Timeframe, VolumeContext
from oracle.domain.shared.base import ValueObject


class Symbol(ValueObject):
    """Normalized asset symbol — always uppercase, stripped whitespace."""

    value: str

    @field_validator("value")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.upper().strip()

    def __str__(self) -> str:
        return self.value


class OHLCVBar(ValueObject):
    """Single OHLCV candlestick — the atomic unit of market data.

    Validates OHLC consistency on construction. Used by both the Market
    context (live data) and the Replay context (historical data).
    """

    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    is_complete: bool = True

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "OHLCVBar":
        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= open and close")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= open and close")
        return self

    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def body_pct(self) -> float:
        """Body size as % of open price."""
        if self.open == 0:
            return 0.0
        return round(self.body_size / self.open * 100, 4)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


class Ticker(ValueObject):
    """Live price quote — ephemeral, not persisted long-term."""

    symbol: str
    price: float = Field(gt=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    spread: float = Field(ge=0)
    volume: float = Field(ge=0)
    timestamp: datetime
    session: MarketSession = MarketSession.REGULAR
    volume_context: VolumeContext = VolumeContext.AT_AVERAGE
