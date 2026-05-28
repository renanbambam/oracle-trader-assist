"""Integration tests for ReflectOnTradeUseCase — real PostgreSQL, fake AI."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from oracle.application.trade.reflect_on_trade import ReflectOnTradeUseCase
from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository
from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


class FakeAIProvider:
    async def complete(self, prompt: str, system: str, image_b64=None) -> str:
        return "## O QUE FUNCIONOU\nSetup bem executado.\n## LIÇÃO PRINCIPAL\nAguardar confirmação."

    async def stream_message(self, message, system):
        yield "token"

    async def stream(self, messages, system):
        yield "token"

    async def count_tokens(self, text: str) -> int:
        return len(text.split())


class FakeEventBus:
    def __init__(self):
        self.published = []

    async def publish(self, channel, event, payload):
        self.published.append((channel, event, payload))

    def subscribe(self, channels):
        return iter([])


def _closed_trade() -> Trade:
    return Trade(
        asset="PETR4",
        direction=Direction.LONG,
        timeframe=Timeframe.M15,
        entry=28.0,
        stop=27.5,
        target=29.0,
        setup="breakout",
        emotional_state=EmotionalState.CALMO,
        opened_at=datetime.now(timezone.utc),
        status=TradeStatus.CLOSED,
        exit=29.0,
        result=TradeResult.WIN,
        r_realized=2.0,
        closed_at=datetime.now(timezone.utc),
    )


async def test_reflect_on_trade_saves_reflection(session):
    trade_repo = PostgresTradeRepository(session)
    memory_repo = PostgresMemoryRepository(session)
    trade = _closed_trade()
    await trade_repo.save(trade)

    use_case = ReflectOnTradeUseCase(
        trade_repo=trade_repo,
        memory_store=memory_repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )

    result = await use_case.execute(trade.id)

    assert "FUNCIONOU" in result.reflection
    assert result.trade_id == trade.id
    assert result.memory_record_id is not None


async def test_reflect_on_trade_persists_memory_record(session):
    trade_repo = PostgresTradeRepository(session)
    memory_repo = PostgresMemoryRepository(session)
    trade = _closed_trade()
    await trade_repo.save(trade)

    use_case = ReflectOnTradeUseCase(
        trade_repo=trade_repo,
        memory_store=memory_repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )
    result = await use_case.execute(trade.id)

    records = await memory_repo.get_records_by_asset("PETR4", limit=20)
    assert any(str(r.id) == str(result.memory_record_id) for r in records)


async def test_reflect_on_open_trade_raises(session):
    trade_repo = PostgresTradeRepository(session)
    memory_repo = PostgresMemoryRepository(session)
    trade = Trade(
        asset="VALE3",
        direction=Direction.SHORT,
        timeframe=Timeframe.M5,
        entry=68.0,
        stop=68.5,
        target=66.0,
        setup="reversal",
        emotional_state=EmotionalState.CALMO,
        opened_at=datetime.now(timezone.utc),
    )
    await trade_repo.save(trade)

    use_case = ReflectOnTradeUseCase(
        trade_repo=trade_repo,
        memory_store=memory_repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )

    with pytest.raises(ValueError, match="must be closed"):
        await use_case.execute(trade.id)
