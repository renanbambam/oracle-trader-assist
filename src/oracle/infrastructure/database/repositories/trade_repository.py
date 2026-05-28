"""PostgreSQL implementation of TradeRepository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import Direction, EmotionalState, TradeResult, TradeStatus
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.models.trade_model import TradeOrm


def _to_orm(trade: Trade) -> TradeOrm:
    return TradeOrm(
        id=trade.id,
        created_at=trade.created_at,
        updated_at=trade.updated_at,
        asset=trade.asset,
        direction=str(trade.direction),
        timeframe=str(trade.timeframe),
        status=str(trade.status),
        entry=trade.entry,
        stop=trade.stop,
        target=trade.target,
        exit=trade.exit,
        result=str(trade.result) if trade.result else None,
        r_realized=trade.r_realized,
        setup=trade.setup,
        emotional_state=str(trade.emotional_state),
        confidence_score=trade.confidence_score,
        analysis_id=str(trade.analysis_id) if trade.analysis_id else None,
        notes=trade.notes,
        reflection=trade.reflection,
        opened_at=trade.opened_at,
        closed_at=trade.closed_at,
    )


def _to_domain(row: TradeOrm) -> Trade:
    return Trade(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        asset=row.asset,
        direction=Direction(row.direction),
        timeframe=Timeframe(row.timeframe),
        status=TradeStatus(row.status),
        entry=row.entry,
        stop=row.stop,
        target=row.target,
        exit=row.exit,
        result=TradeResult(row.result) if row.result else None,
        r_realized=row.r_realized,
        setup=row.setup,
        emotional_state=EmotionalState(row.emotional_state),
        confidence_score=row.confidence_score,
        analysis_id=UUID(row.analysis_id) if row.analysis_id else None,
        notes=row.notes,
        reflection=row.reflection,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
    )


class PostgresTradeRepository:
    """Concrete TradeRepository backed by PostgreSQL via SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trade: Trade) -> Trade:
        row = _to_orm(trade)
        self._session.add(row)
        await self._session.flush()
        return trade

    async def get_by_id(self, trade_id: UUID) -> Trade | None:
        result = await self._session.get(TradeOrm, trade_id)
        return _to_domain(result) if result else None

    async def update(self, trade: Trade) -> Trade:
        result = await self._session.get(TradeOrm, trade.id)
        if result is None:
            raise ValueError(f"Trade {trade.id} not found")
        row = _to_orm(trade)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.merge(row)
        await self._session.flush()
        return trade

    async def get_by_status(self, status: TradeStatus) -> list[Trade]:
        stmt = select(TradeOrm).where(TradeOrm.status == str(status))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_by_asset(self, asset: str, limit: int = 20) -> list[Trade]:
        stmt = (
            select(TradeOrm)
            .where(TradeOrm.asset == asset)
            .order_by(TradeOrm.opened_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_recent(self, limit: int = 50) -> list[Trade]:
        stmt = select(TradeOrm).order_by(TradeOrm.opened_at.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
