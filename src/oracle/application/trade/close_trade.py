"""CloseTradeUseCase — closes an open trade and computes realized R."""

from datetime import datetime, timezone

from oracle.application.trade.dtos import CloseTradeInput, TradeOutput
from oracle.application.trade.record_trade import trade_to_output
from oracle.core.ports import EventBus
from oracle.domain.trade.enums import TradeStatus
from oracle.domain.trade.events import TradeClosed


class CloseTradeUseCase:
    def __init__(self, repository, event_bus: EventBus) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def execute(self, data: CloseTradeInput) -> TradeOutput:
        trade = await self._repo.get_by_id(data.trade_id)
        if trade is None:
            raise ValueError(f"Trade {data.trade_id} not found")
        if trade.status != TradeStatus.OPEN:
            raise ValueError(f"Trade {data.trade_id} is already closed")

        trade.exit = data.exit_price
        trade.result = data.result
        trade.closed_at = datetime.now(timezone.utc)
        trade.status = TradeStatus.CLOSED

        rr = trade.risk_ratio
        if trade.direction == "LONG":
            trade.r_realized = round((data.exit_price - trade.entry) / rr.risk_points, 2)
        else:
            trade.r_realized = round((trade.entry - data.exit_price) / rr.risk_points, 2)

        if data.notes:
            trade.notes = (trade.notes or "") + f"\n[close] {data.notes}"

        updated = await self._repo.update(trade)

        await self._event_bus.publish(
            channel="trading",
            event="trade.closed",
            payload=TradeClosed(
                trade_id=updated.id,
                asset=updated.asset,
                direction=updated.direction,
                result=updated.result,
                r_realized=updated.r_realized or 0.0,
                exit_price=data.exit_price,
                session_id=None,
            ).model_dump(mode="json"),
        )

        return trade_to_output(updated)
