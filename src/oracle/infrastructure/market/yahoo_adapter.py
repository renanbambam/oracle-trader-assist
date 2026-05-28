"""YahooMarketAdapter — real market data via yfinance.

Wraps the synchronous yfinance library in async-friendly calls using
run_in_executor so the event loop is never blocked.

Symbol mapping:
  Brazilian stocks → symbol.SA (e.g. PETR4 → PETR4.SA)
  Indices         → ^BVSP for IBOV
  Forex           → EURUSD=X, USDJPY=X
  Commodities     → GC=F (gold), SI=F (silver)
  Futures         → NQ=F (US100)

Symbols not available on Yahoo (WINFUT, WINQ, DOLFUT) fall back to
MockMarketAdapter transparently — callers don't need to know.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from loguru import logger

from oracle.domain.market.entities import MarketSnapshot
from oracle.domain.market.enums import AssetClass, MarketSession, Timeframe, VolumeContext
from oracle.domain.market.value_objects import OHLCVBar, Ticker
from oracle.infrastructure.market.mock_adapter import MockMarketAdapter

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    yf = None  # type: ignore[assignment]
    _YF_AVAILABLE = False

# Mapping from internal symbol → Yahoo Finance ticker
_YAHOO_MAP: dict[str, str | None] = {
    "PETR4":  "PETR4.SA",
    "VALE3":  "VALE3.SA",
    "ITUB4":  "ITUB4.SA",
    "BBDC4":  "BBDC4.SA",
    "IBOV":   "^BVSP",
    "WINQ":   None,       # B3 mini-index futures — not on Yahoo
    "WINFUT": None,
    "DOLFUT": None,
    "EURUSD": "EURUSD=X",
    "XAUUSD": "GC=F",
    "US100":  "NQ=F",
    "USDJPY": "USDJPY=X",
}

_TF_INTERVAL: dict[str, str] = {
    "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
    "H1": "1h", "H4": "1h", "D1": "1d", "W1": "1wk",
}
_TF_PERIOD: dict[str, str] = {
    "M1": "1d", "M5": "5d", "M15": "5d", "M30": "5d",
    "H1": "60d", "H4": "60d", "D1": "1y", "W1": "5y",
}

_mock = MockMarketAdapter()


def _yahoo_sym(symbol: str) -> str | None:
    return _YAHOO_MAP.get(symbol.upper())


def _asset_class(symbol: str) -> AssetClass:
    up = symbol.upper()
    if any(x in up for x in ("FUT", "WINQ", "DOLFUT")):
        return AssetClass.FUTURES
    if any(x in up for x in ("USD", "EUR", "JPY", "GBP", "XAU", "GC=", "NQ=")):
        return AssetClass.FOREX
    return AssetClass.STOCK


def _fetch_history(yahoo_sym: str, interval: str, period: str):
    """Sync fetch — runs in thread executor."""
    ticker = yf.Ticker(yahoo_sym)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    return df


def _fetch_fast_info(yahoo_sym: str):
    """Sync fetch of fast_info — runs in thread executor."""
    ticker = yf.Ticker(yahoo_sym)
    return ticker.fast_info


def _df_to_bars(df, symbol: str, timeframe: Timeframe) -> list[OHLCVBar]:
    bars: list[OHLCVBar] = []
    if df is None or df.empty:
        return bars
    for ts, row in df.iterrows():
        try:
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            bars.append(OHLCVBar(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=dt,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0) or 0),
            ))
        except Exception:
            continue
    return bars


class YahooMarketAdapter:
    """Real market data from Yahoo Finance via yfinance.

    Falls back to MockMarketAdapter for symbols not available on Yahoo
    (e.g. B3 futures WINFUT, WINQ) and when Yahoo is unreachable.
    """

    async def get_snapshot(self, symbol: str, timeframe: Timeframe) -> MarketSnapshot:
        yahoo_sym = _yahoo_sym(symbol)
        if not yahoo_sym or not _YF_AVAILABLE:
            return await _mock.get_snapshot(symbol, timeframe)

        try:
            loop = asyncio.get_running_loop()
            interval = _TF_INTERVAL.get(str(timeframe), "5m")
            period = _TF_PERIOD.get(str(timeframe), "5d")

            df = await loop.run_in_executor(None, _fetch_history, yahoo_sym, interval, period)
            bars = _df_to_bars(df, symbol, timeframe)

            if not bars:
                logger.warning(f"YahooAdapter: no bars for {yahoo_sym}, falling back to Mock")
                return await _mock.get_snapshot(symbol, timeframe)

            last = bars[-1]
            price = last.close
            spread = round(price * 0.0002, 5)

            return MarketSnapshot(
                symbol=symbol,
                timeframe=timeframe,
                asset_class=_asset_class(symbol),
                session=MarketSession.REGULAR,
                current_price=price,
                bid=round(price - spread / 2, 5),
                ask=round(price + spread / 2, 5),
                spread=spread,
                current_bar=last,
                recent_bars=bars[-20:],
                captured_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.warning(f"YahooAdapter.get_snapshot({symbol}) failed: {exc} — using Mock")
            return await _mock.get_snapshot(symbol, timeframe)

    async def get_historical(self, symbol: str, timeframe: Timeframe, count: int) -> list[OHLCVBar]:
        yahoo_sym = _yahoo_sym(symbol)
        if not yahoo_sym or not _YF_AVAILABLE:
            return await _mock.get_historical(symbol, timeframe, count)

        try:
            loop = asyncio.get_running_loop()
            interval = _TF_INTERVAL.get(str(timeframe), "5m")
            period = _TF_PERIOD.get(str(timeframe), "5d")
            df = await loop.run_in_executor(None, _fetch_history, yahoo_sym, interval, period)
            bars = _df_to_bars(df, symbol, timeframe)
            return bars[-count:] if len(bars) >= count else bars
        except Exception as exc:
            logger.warning(f"YahooAdapter.get_historical({symbol}) failed: {exc} — using Mock")
            return await _mock.get_historical(symbol, timeframe, count)

    async def get_price(self, symbol: str) -> float:
        try:
            snap = await self.get_snapshot(symbol, Timeframe.M5)
            return snap.current_price
        except Exception:
            return await _mock.get_price(symbol)

    async def is_market_open(self, symbol: str) -> bool:
        return await _mock.is_market_open(symbol)

    async def _tick_stream(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        # Real tick streaming requires WebSocket connections not available in yfinance.
        # Delegate to Mock for tick simulation.
        async for tick in _mock._tick_stream(symbol):
            yield tick

    def stream_ticks(self, symbol: str) -> AsyncGenerator[Ticker, None]:
        return self._tick_stream(symbol)
