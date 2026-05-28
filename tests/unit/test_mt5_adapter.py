"""Unit tests for MT5Adapter — MetaTrader5 library is fully mocked."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from oracle.domain.market.enums import Timeframe


# ── Shared MT5 stub ──────────────────────────────────────────────────────────

def _make_mt5():
    """Build a minimal stand-in for the MetaTrader5 module."""
    m = MagicMock()
    # Timeframe constants
    m.TIMEFRAME_M1  = 1;   m.TIMEFRAME_M5  = 5;   m.TIMEFRAME_M15 = 15
    m.TIMEFRAME_M30 = 30;  m.TIMEFRAME_H1  = 60;  m.TIMEFRAME_H4  = 240
    m.TIMEFRAME_D1  = 1440; m.TIMEFRAME_W1 = 10080; m.TIMEFRAME_MN1 = 43200
    m.initialize.return_value = True
    m.shutdown.return_value   = True
    m.last_error.return_value = (0, "ok")
    return m


def _tick(bid=28.50, ask=28.52, last=28.51, volume=1000, time=1_700_000_000):
    return SimpleNamespace(bid=bid, ask=ask, last=last, volume=volume, time=time)


def _rates(symbol="PETR4", n=5):
    base = 28.00
    rows = []
    for i in range(n):
        o = round(base + i * 0.10, 2)
        rows.append({
            "time": 1_700_000_000 + i * 3600,
            "open": o, "high": o + 0.05, "low": o - 0.05, "close": o + 0.02,
            "tick_volume": 500, "real_volume": 0,
        })
    return rows


def _info(trade_mode=3):
    return SimpleNamespace(trade_mode=trade_mode)


@pytest.fixture
def mt5(monkeypatch):
    stub = _make_mt5()
    monkeypatch.setattr("oracle.infrastructure.market.mt5_adapter.mt5", stub)
    monkeypatch.setattr("oracle.infrastructure.market.mt5_adapter._MT5_AVAILABLE", True)
    return stub


@pytest.fixture
def settings():
    s = MagicMock()
    s.MT5_LOGIN    = 12345678
    s.MT5_PASSWORD = "secret"
    s.MT5_SERVER   = "Broker-Demo"
    return s


@pytest.fixture
def adapter(settings, mt5):
    from oracle.infrastructure.market.mt5_adapter import MT5Adapter
    return MT5Adapter(settings)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_raises_when_mt5_not_installed(settings, monkeypatch):
    monkeypatch.setattr("oracle.infrastructure.market.mt5_adapter._MT5_AVAILABLE", False)
    from oracle.infrastructure.market.mt5_adapter import MT5Adapter
    with pytest.raises(RuntimeError, match="not installed"):
        MT5Adapter(settings)


@pytest.mark.asyncio
async def test_connect_calls_initialize(adapter, mt5):
    mt5.initialize.return_value = True
    await adapter.connect()
    mt5.initialize.assert_called_once_with(
        login=adapter._login,
        password=adapter._password,
        server=adapter._server,
    )


@pytest.mark.asyncio
async def test_connect_raises_on_failure(adapter, mt5):
    mt5.initialize.return_value = False
    with pytest.raises(RuntimeError, match="initialize failed"):
        await adapter.connect()


@pytest.mark.asyncio
async def test_get_price_returns_last_price(adapter, mt5):
    mt5.symbol_info_tick.return_value = _tick(last=28.51)
    price = await adapter.get_price("PETR4")
    assert price == pytest.approx(28.51)
    mt5.symbol_info_tick.assert_called_once_with("PETR4")


@pytest.mark.asyncio
async def test_get_price_falls_back_to_bid_when_last_is_zero(adapter, mt5):
    mt5.symbol_info_tick.return_value = _tick(bid=28.40, last=0)
    price = await adapter.get_price("PETR4")
    assert price == pytest.approx(28.40)


@pytest.mark.asyncio
async def test_get_price_raises_when_no_tick(adapter, mt5):
    mt5.symbol_info_tick.return_value = None
    with pytest.raises(RuntimeError, match="no price"):
        await adapter.get_price("PETR4")


@pytest.mark.asyncio
async def test_get_historical_maps_rates_to_bars(adapter, mt5):
    mt5.copy_rates_from_pos.return_value = _rates(n=3)
    bars = await adapter.get_historical("PETR4", Timeframe.H1, count=3)
    assert len(bars) == 3
    assert bars[0].symbol == "PETR4"
    assert bars[0].timeframe == Timeframe.H1
    assert bars[0].open == pytest.approx(28.00)
    mt5.copy_rates_from_pos.assert_called_once_with("PETR4", 60, 0, 3)


@pytest.mark.asyncio
async def test_get_historical_returns_empty_on_no_data(adapter, mt5):
    mt5.copy_rates_from_pos.return_value = None
    bars = await adapter.get_historical("PETR4", Timeframe.H1, count=5)
    assert bars == []


@pytest.mark.asyncio
async def test_is_market_open_true_when_trade_mode_nonzero(adapter, mt5):
    mt5.symbol_info.return_value = _info(trade_mode=3)
    assert await adapter.is_market_open("PETR4") is True


@pytest.mark.asyncio
async def test_is_market_open_false_when_disabled(adapter, mt5):
    mt5.symbol_info.return_value = _info(trade_mode=0)
    assert await adapter.is_market_open("PETR4") is False


@pytest.mark.asyncio
async def test_is_market_open_false_when_symbol_not_found(adapter, mt5):
    mt5.symbol_info.return_value = None
    assert await adapter.is_market_open("UNKNOWN") is False


@pytest.mark.asyncio
async def test_get_snapshot_builds_market_snapshot(adapter, mt5):
    mt5.symbol_info_tick.return_value = _tick(bid=28.50, ask=28.52, last=28.51)
    mt5.copy_rates_from_pos.return_value = _rates(n=20)
    mt5.symbol_info.return_value = _info(trade_mode=3)

    snap = await adapter.get_snapshot("PETR4", Timeframe.H1)

    assert snap.symbol == "PETR4"
    assert snap.bid == pytest.approx(28.50)
    assert snap.ask == pytest.approx(28.52)
    assert snap.spread == pytest.approx(0.02)
    assert len(snap.recent_bars) == 20
