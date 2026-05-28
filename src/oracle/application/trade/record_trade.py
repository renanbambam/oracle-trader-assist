"""RecordTradeUseCase — validates and persists a new trade entry."""

from datetime import datetime, timezone

from oracle.application.trade.dtos import RecordTradeInput, TradeOutput
from oracle.core.ports import EventBus
from oracle.domain.trade.entities import Trade
from oracle.domain.trade.events import TradeOpened


class RecordTradeUseCase:
    def __init__(self, repository, event_bus: EventBus) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def execute(self, data: RecordTradeInput) -> TradeOutput:
        trade = Trade(
            asset=data.asset,
            direction=data.direction,
            timeframe=data.timeframe,
            entry=data.entry,
            stop=data.stop,
            target=data.target,
            setup=data.setup,
            emotional_state=data.emotional_state,
            analysis_id=data.analysis_id,
            notes=data.notes,
            opened_at=datetime.now(timezone.utc),
        )

        saved = await self._repo.save(trade)

        await self._event_bus.publish(
            channel="trading",
            event="trade.opened",
            payload=TradeOpened(
                trade_id=saved.id,
                asset=saved.asset,
                direction=saved.direction,
                entry=saved.entry,
                stop=saved.stop,
                target=saved.target,
                setup=saved.setup,
                session_id=None,
            ).model_dump(mode="json"),
        )

        return trade_to_output(saved)

    async def list_recent(self, limit: int = 50) -> list[TradeOutput]:
        trades = await self._repo.get_recent(limit=limit)
        return [trade_to_output(t) for t in trades]


def trade_to_output(trade: Trade) -> TradeOutput:
    return TradeOutput(
        id=trade.id,
        asset=trade.asset,
        direction=trade.direction,
        timeframe=trade.timeframe,
        status=trade.status,
        entry=trade.entry,
        stop=trade.stop,
        target=trade.target,
        exit=trade.exit,
        result=trade.result,
        r_realized=trade.r_realized,
        rr_ratio=trade.risk_ratio.rr,
        setup=trade.setup,
        emotional_state=trade.emotional_state,
        confidence_score=trade.confidence_score,
        created_at=trade.created_at,
        closed_at=trade.closed_at,
    )
