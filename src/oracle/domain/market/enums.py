"""Market domain — enumerations."""

from enum import StrEnum


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN = "MN"


class AssetClass(StrEnum):
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    INDEX = "index"
    COMMODITY = "commodity"
    FUTURES = "futures"


class MarketSession(StrEnum):
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_MARKET = "after_market"
    CLOSED = "closed"


class VolumeContext(StrEnum):
    ABOVE_AVERAGE = "above_avg"
    BELOW_AVERAGE = "below_avg"
    AT_AVERAGE = "at_avg"
    HIGH_SPIKE = "high_spike"
