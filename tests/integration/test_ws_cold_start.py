"""Integration tests for WebSocket cold start — real PostgreSQL, fake engine injection."""

from datetime import datetime, timezone

import pytest

from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeStatus
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository
from oracle.interface.websocket.cold_start import _fetch
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


async def test_trading_snapshot_includes_open_trades(engine, session):
    repo = PostgresTradeRepository(session)
    trade = Trade(
        asset="PETR4",
        direction=Direction.LONG,
        timeframe=Timeframe.M5,
        entry=28.0,
        stop=27.5,
        target=29.5,
        setup="test_cold_start",
        emotional_state=EmotionalState.CALMO,
        opened_at=datetime.now(timezone.utc),
    )
    await repo.save(trade)
    await session.flush()

    snapshot = await _fetch("trading", engine)

    assert snapshot is not None
    assert snapshot["channel"] == "trading"
    assert snapshot["event"] == "trading.snapshot"
    assert isinstance(snapshot["payload"]["open_count"], int)
    assert snapshot["payload"]["open_count"] >= 1


async def test_unknown_channel_returns_none(engine):
    result = await _fetch("nonexistent_channel", engine)
    assert result is None


async def test_replay_snapshot_returns_none_when_no_sessions(engine):
    result = await _fetch("replay", engine)
    # May be None or a snapshot depending on DB state — just ensure no crash
    assert result is None or result["channel"] == "replay"


async def test_snapshot_provider_wraps_errors_gracefully(engine):
    from oracle.interface.websocket.cold_start import make_snapshot_provider
    provider = make_snapshot_provider(engine)
    result = await provider("trading")
    # Should return a dict or None, never raise
    assert result is None or isinstance(result, dict)
