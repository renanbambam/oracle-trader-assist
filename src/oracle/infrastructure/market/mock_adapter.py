"""MockMarketAdapter — synthetic market data for development and testing.

Implements MarketDataProvider without MT5. Generates deterministic-looking
prices via a seeded random walk so tests stay reproducible.
"""

import random
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

from oracle.domain.market.entities import MarketSnapshot
from oracle.domain.market.enums import AssetClass, MarketSession, Timeframe, VolumeContext
from oracle.domain.market.value_objects import OHLCVBar, Ticker

_BASE_PRICES: dict[str, float] = {
    "PETR4": 28.50, "VALE3": 68.00, "ITUB4": 30.00, "BBDC4": 16.00,
    "WINFUT": 130_000.0, "DOLFUT": 5_200.0,
    "IBOV": 131_000.0, "WINQ": 131_000.0,
    "EURUSD": 1.0850, "XAUUSD": 2_300.0, "US100": 17_500.0, "USDJPY": 150.0,
}
_TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440, "W1": 10080,
}


def _base_price(symbol: str) -> float:
    return _BASE_PRICES.get(symbol.upper(), 100.0)


def _random_bar(symbol: str, timeframe: Timeframe, ts: datetime, seed_price: float) -> OHLCVBar:
    rng = random.Random(hash((symbol, str(ts))))
    open_p = round(seed_price, 2)
    close_p = round(open_p * (1 + rng.gauss(0, 0.003)), 2)
    high_p = round(max(open_p, close_p) * (1 + abs(rng.gauss(0, 0.001))), 2)
    low_p = round(min(open_p, close_p) * max(0.001, 1 - abs(rng.gauss(0, 0.001))), 2)
    volume = round(rng.uniform(5_000, 100_000), 0)
    return OHLCVBar(
        symbol=symbol, timeframe=timeframe, timestamp=ts,
        open=open_p, high=high_p, low=low_p, close=close_p, volume=volume,
    )


class MockMarketAdapter:
    """Synthetic implementation of MarketDataProvider.

    All data is generated from a price model — no network calls.
    Safe to use in tests, CI, and offline development.
    """

    async def get_snapshot(self, symbol: str, timeframe: Timeframe) -> MarketSnapshot:
        now = datetime.now(timezone.utc)
        price = _base_price(symbol)
        bar = _random_bar(symbol, timeframe, now, price)
        spread = round(price * 0.0002, 4)

        bars = await self.get_historical(symbol, timeframe, count=20)

        return MarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            asset_class=AssetClass.FUTURES if "FUT" in symbol.upper() else AssetClass.STOCK,
            session=MarketSession.REGULAR,
            current_price=bar.close,
            bid=round(bar.close - spread / 2, 2),
            ask=round(bar.close + spread / 2, 2),
            spread=spread,
            current_bar=bar,
            recent_bars=bars,
            captured_at=now,
        )

    async def get_historical(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int,
    ) -> list[OHLCVBar]:
        interval = _TIMEFRAME_MINUTES.get(str(timeframe), 5)
        now = datetime.now(timezone.utc)
        price = _base_price(symbol)
        bars: list[OHLCVBar] = []

        for i in range(count, 0, -1):
            ts = now - timedelta(minutes=interval * i)
            bar = _random_bar(symbol, timeframe, ts, price)
            bars.append(bar)
            price = bar.close

        return bars

    async def get_price(self, symbol: str) -> float:
        price = _base_price(symbol)
        rng = random.Random(hash((symbol, datetime.now(timezone.utc).minute)))
        return round(price * (1 + rng.gauss(0, 0.002)), 2)

    async def is_market_open(self, symbol: str) -> bool:
        now = datetime.now(timezone.utc)
        # Brazilian market: Mon–Fri, 13:00–21:00 UTC (approx)
        if now.weekday() >= 5:
            return False
        return 13 <= now.hour < 21

    async def _tick_stream(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        price = _base_price(symbol)
        while True:
            spread = round(price * 0.0002, 4)
            yield Ticker(
                symbol=symbol,
                price=price,
                bid=round(price - spread / 2, 2),
                ask=round(price + spread / 2, 2),
                spread=spread,
                volume=round(random.uniform(100, 1_000), 0),
                timestamp=datetime.now(timezone.utc),
                volume_context=VolumeContext.AT_AVERAGE,
            )
            price = round(price * (1 + random.gauss(0, 0.001)), 2)

    def stream_ticks(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        return self._tick_stream(symbol)
