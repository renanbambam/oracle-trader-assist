"""ReflectOnTradeUseCase — generates and persists a post-trade AI reflection."""

from uuid import UUID

from oracle.application.trade.dtos import ReflectionOutput
from oracle.core.ports import EventBus
from oracle.domain.memory.entities import MemoryRecord
from oracle.domain.memory.contracts import MemoryStore
from oracle.domain.trade.contracts import TradeRepository
from oracle.domain.trade.enums import TradeStatus
from prompts.system.oracle_system_v1 import TEMPLATE as SYSTEM_PROMPT
from prompts.trade.reflection import build_prompt


class ReflectOnTradeUseCase:
    """Calls Claude with post-trade data, persists the reflection as a MemoryRecord."""

    def __init__(
        self,
        trade_repo: TradeRepository,
        memory_store: MemoryStore,
        ai_provider,   # AIProvider Protocol
        event_bus: EventBus,
    ) -> None:
        self._trades = trade_repo
        self._memory = memory_store
        self._ai = ai_provider
        self._event_bus = event_bus

    async def execute(self, trade_id: UUID) -> ReflectionOutput:
        trade = await self._trades.get_by_id(trade_id)
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found")
        if trade.status != TradeStatus.CLOSED:
            raise ValueError(f"Trade {trade_id} must be closed before reflection")
        if trade.exit is None or trade.result is None:
            raise ValueError(f"Trade {trade_id} is missing exit data")

        prompt = build_prompt(
            asset=trade.asset,
            direction=str(trade.direction),
            timeframe=str(trade.timeframe),
            setup=trade.setup,
            entry=trade.entry,
            stop=trade.stop,
            target=trade.target,
            exit_price=trade.exit,
            result=str(trade.result),
            r_realized=trade.r_realized or 0.0,
            emotional_state=str(trade.emotional_state),
            notes=trade.notes,
        )

        reflection_text = await self._ai.complete(prompt=prompt, system=SYSTEM_PROMPT)

        trade.reflection = reflection_text
        await self._trades.update(trade)

        record = MemoryRecord(
            asset=trade.asset,
            setup_type=trade.setup,
            content=reflection_text,
            source_trade_id=trade.id,
        )
        saved_record = await self._memory.save_record(record)

        await self._event_bus.publish(
            channel="trading",
            event="trade.reflected",
            payload={
                "trade_id": str(trade.id),
                "asset": trade.asset,
                "result": str(trade.result),
                "memory_record_id": str(saved_record.id),
            },
        )

        return ReflectionOutput(
            trade_id=trade.id,
            reflection=reflection_text,
            memory_record_id=saved_record.id,
        )
