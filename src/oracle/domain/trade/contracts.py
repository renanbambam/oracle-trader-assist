"""Trade domain — contracts (protocols/interfaces)."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from oracle.domain.trade.entities import Trade
from oracle.domain.trade.enums import TradeStatus


@runtime_checkable
class TradeRepository(Protocol):
    """Port for persisting and querying trade records.

    Implemented by PostgresTradeRepository in infrastructure/database/.
    """

    async def save(self, trade: Trade) -> Trade: ...

    async def get_by_id(self, trade_id: UUID) -> Trade | None: ...

    async def update(self, trade: Trade) -> Trade: ...

    async def get_by_status(self, status: TradeStatus) -> list[Trade]: ...

    async def get_by_asset(self, asset: str, limit: int = 20) -> list[Trade]: ...

    async def get_recent(self, limit: int = 50) -> list[Trade]: ...
