"""Integration tests for PostgresTradeRepository — real PostgreSQL."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from oracle.domain.market.enums import Timeframe
from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus
from oracle.infrastructure.database.repositories.trade_repository import (
    PostgresTradeRepository,
)
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


def _trade(**overrides) -> Trade:
    defaults = dict(
        asset="PETR4",
        direction=Direction.LONG,
        timeframe=Timeframe.M5,
        entry=20.0,
        stop=19.0,
        target=22.0,
        setup="breakout",
        emotional_state=EmotionalState.CALMO,
        opened_at=datetime.now(timezone.utc),
    )
    return Trade(**{**defaults, **overrides})


async def test_save_and_get_by_id(session):
    repo = PostgresTradeRepository(session)
    trade = _trade()

    await repo.save(trade)
    found = await repo.get_by_id(trade.id)

    assert found is not None
    assert found.id == trade.id
    assert found.asset == "PETR4"
    assert found.direction == Direction.LONG
    assert found.entry == 20.0
    assert found.status == TradeStatus.OPEN


async def test_get_by_id_not_found_returns_none(session):
    repo = PostgresTradeRepository(session)
    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_save_persists_all_required_fields(session):
    repo = PostgresTradeRepository(session)
    trade = _trade(
        asset="WINFUT",
        direction=Direction.SHORT,
        timeframe=Timeframe.M15,
        entry=130000.0,
        stop=130200.0,
        target=129400.0,
        setup="reversal",
        emotional_state=EmotionalState.CONFIANTE,
    )

    await repo.save(trade)
    found = await repo.get_by_id(trade.id)

    assert found.asset == "WINFUT"
    assert found.direction == Direction.SHORT
    assert found.timeframe == Timeframe.M15
    assert found.emotional_state == EmotionalState.CONFIANTE


async def test_update_closes_trade(session):
    repo = PostgresTradeRepository(session)
    trade = _trade()
    await repo.save(trade)

    trade.status = TradeStatus.CLOSED
    trade.exit = 21.5
    trade.result = TradeResult.WIN
    trade.r_realized = 1.5
    trade.closed_at = datetime.now(timezone.utc)

    await repo.update(trade)
    found = await repo.get_by_id(trade.id)

    assert found.status == TradeStatus.CLOSED
    assert found.exit == 21.5
    assert found.result == TradeResult.WIN
    assert found.r_realized == 1.5
    assert found.closed_at is not None


async def test_get_recent_returns_newest_first(session):
    repo = PostgresTradeRepository(session)
    t1 = _trade(opened_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    t2 = _trade(opened_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    t3 = _trade(opened_at=datetime(2024, 12, 1, tzinfo=timezone.utc))

    for t in [t1, t2, t3]:
        await repo.save(t)

    recent = await repo.get_recent(limit=3)
    dates = [t.opened_at for t in recent]
    assert dates == sorted(dates, reverse=True)


async def test_get_by_status_filters_correctly(session):
    repo = PostgresTradeRepository(session)
    open_trade = _trade()
    closed_trade = _trade(
        status=TradeStatus.CLOSED,
        exit=21.0,
        result=TradeResult.WIN,
        closed_at=datetime.now(timezone.utc),
    )

    await repo.save(open_trade)
    await repo.save(closed_trade)

    open_list = await repo.get_by_status(TradeStatus.OPEN)
    closed_list = await repo.get_by_status(TradeStatus.CLOSED)

    open_ids = {t.id for t in open_list}
    closed_ids = {t.id for t in closed_list}

    assert open_trade.id in open_ids
    assert open_trade.id not in closed_ids
    assert closed_trade.id in closed_ids


async def test_get_by_asset_filters_by_asset(session):
    repo = PostgresTradeRepository(session)
    petr = _trade(asset="PETR4")
    win = _trade(asset="WINFUT", direction=Direction.SHORT,
                 entry=130000.0, stop=130200.0, target=129400.0)

    await repo.save(petr)
    await repo.save(win)

    petr_trades = await repo.get_by_asset("PETR4")
    assert all(t.asset == "PETR4" for t in petr_trades)
    assert any(t.id == petr.id for t in petr_trades)


async def test_enum_roundtrip_serialization(session):
    repo = PostgresTradeRepository(session)
    trade = _trade(emotional_state=EmotionalState.FOMO)

    await repo.save(trade)
    found = await repo.get_by_id(trade.id)

    # Entity.model_config uses use_enum_values=True, so StrEnum is stored as its
    # string value after Pydantic coercion; equality via StrEnum still holds.
    assert found.emotional_state == EmotionalState.FOMO
    assert found.emotional_state == "fomo"
