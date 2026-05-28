"""MT5Adapter — real market data from MetaTrader5.

Windows-only: the MetaTrader5 Python library runs only on Windows with
the MT5 terminal installed and running. Raises RuntimeError on import
on other platforms.

Credentials come from Settings (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER).
All synchronous MT5 calls are dispatched to a thread executor so they
do not block the asyncio event loop.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from oracle.domain.market.entities import MarketSnapshot
from oracle.domain.market.enums import AssetClass, MarketSession, Timeframe, VolumeContext
from oracle.domain.market.value_objects import OHLCVBar, Ticker

try:
    import MetaTrader5 as mt5  # type: ignore[import-untyped]
    _MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore[assignment]
    _MT5_AVAILABLE = False


def _tf(timeframe: Timeframe) -> int:
    """Map Timeframe enum to MT5 constant."""
    return {
        Timeframe.M1:  mt5.TIMEFRAME_M1,
        Timeframe.M5:  mt5.TIMEFRAME_M5,
        Timeframe.M15: mt5.TIMEFRAME_M15,
        Timeframe.M30: mt5.TIMEFRAME_M30,
        Timeframe.H1:  mt5.TIMEFRAME_H1,
        Timeframe.H4:  mt5.TIMEFRAME_H4,
        Timeframe.D1:  mt5.TIMEFRAME_D1,
        Timeframe.W1:  mt5.TIMEFRAME_W1,
        Timeframe.MN:  mt5.TIMEFRAME_MN1,
    }.get(timeframe, mt5.TIMEFRAME_H1)


class MT5Adapter:
    """Concrete MarketDataProvider backed by MetaTrader5."""

    def __init__(self, settings: Any) -> None:
        if not _MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not installed (Windows-only)")
        self._login    = settings.MT5_LOGIN
        self._password = settings.MT5_PASSWORD
        self._server   = settings.MT5_SERVER

    async def connect(self) -> None:
        """Open MT5 connection. Safe to call if already connected."""
        ok = await self._run(mt5.initialize,
                             login=self._login,
                             password=self._password,
                             server=self._server)
        if not ok:
            err = await self._run(mt5.last_error)
            raise RuntimeError(f"MT5 initialize failed: {err}")
        logger.info(f"MT5 connected — server={self._server} login={self._login}")

    async def disconnect(self) -> None:
        """Gracefully close the MT5 connection."""
        await self._run(mt5.shutdown)
        logger.info("MT5 disconnected")

    # ── MarketDataProvider ──────────────────────────────────────────────────

    async def get_snapshot(self, symbol: str, timeframe: Timeframe) -> MarketSnapshot:
        tick = await self._run(mt5.symbol_info_tick, symbol)
        if tick is None:
            raise RuntimeError(f"MT5: no tick for {symbol}")

        bars = await self.get_historical(symbol, timeframe, count=20)
        if not bars:
            raise RuntimeError(f"MT5: no bar data for {symbol} {timeframe}")

        info  = await self._run(mt5.symbol_info, symbol)
        price = tick.last if tick.last > 0 else tick.bid
        spread = round(tick.ask - tick.bid, 5)

        return MarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            asset_class=_classify(symbol),
            session=_session(info),
            current_price=price,
            bid=tick.bid,
            ask=tick.ask,
            spread=spread,
            current_bar=bars[-1],
            recent_bars=bars,
            captured_at=datetime.now(timezone.utc),
        )

    async def get_historical(
        self,
        symbol: str,
        timeframe: Timeframe,
        count: int,
    ) -> list[OHLCVBar]:
        rates = await self._run(
            mt5.copy_rates_from_pos, symbol, _tf(timeframe), 0, count
        )
        if rates is None or len(rates) == 0:
            return []
        return [_to_bar(symbol, timeframe, r) for r in rates]

    async def get_price(self, symbol: str) -> float:
        tick = await self._run(mt5.symbol_info_tick, symbol)
        if tick is None:
            raise RuntimeError(f"MT5: no price for {symbol}")
        return float(tick.last if tick.last > 0 else tick.bid)

    async def is_market_open(self, symbol: str) -> bool:
        info = await self._run(mt5.symbol_info, symbol)
        if info is None:
            return False
        # trade_mode 0 = disabled (market closed), >0 = some form of trading allowed
        return int(getattr(info, "trade_mode", 0)) > 0

    async def _tick_stream(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        while True:
            tick = await self._run(mt5.symbol_info_tick, symbol)
            if tick is not None:
                yield Ticker(
                    symbol=symbol,
                    price=float(tick.last if tick.last > 0 else tick.bid),
                    bid=float(tick.bid),
                    ask=float(tick.ask),
                    spread=round(float(tick.ask - tick.bid), 5),
                    volume=float(tick.volume),
                    timestamp=datetime.fromtimestamp(int(tick.time), tz=timezone.utc),
                    volume_context=VolumeContext.AT_AVERAGE,
                )
            await asyncio.sleep(0.5)

    def stream_ticks(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        return self._tick_stream(symbol)

    # ── Internal ───────────────────────────────────────────────────────────

    async def _run(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_bar(symbol: str, timeframe: Timeframe, r: Any) -> OHLCVBar:
    ts  = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
    vol = float(r.get("real_volume") or r.get("tick_volume") or 0)
    return OHLCVBar(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        open=float(r["open"]),
        high=float(r["high"]),
        low=float(r["low"]),
        close=float(r["close"]),
        volume=vol,
    )


def _classify(symbol: str) -> AssetClass:
    s = symbol.upper()
    if any(s.startswith(p) for p in ("WIN", "DOL", "IND", "WDO")) or s.endswith("FUT"):
        return AssetClass.FUTURES
    if len(s) == 6 and s.isalpha():  # EURUSD, GBPJPY etc.
        return AssetClass.FOREX
    return AssetClass.STOCK


def _session(info: Any) -> MarketSession:
    if info is None:
        return MarketSession.CLOSED
    return MarketSession.REGULAR if int(getattr(info, "trade_mode", 0)) > 0 else MarketSession.CLOSED
