"""Memory domain — contracts (protocols/interfaces)."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from oracle.domain.memory.entities import ContextSession, MemoryRecord


@runtime_checkable
class MemoryStore(Protocol):
    """Port for persisting and querying context sessions and memory records.

    Implemented by PostgresMemoryRepository in infrastructure/database/.
    """

    async def save_session(self, session: ContextSession) -> ContextSession: ...

    async def get_session(self, session_id: UUID) -> ContextSession | None: ...

    async def get_active_session(self, asset: str) -> ContextSession | None: ...

    async def expire_session(self, session_id: UUID) -> None: ...

    async def save_record(self, record: MemoryRecord) -> MemoryRecord: ...

    async def get_records_by_asset(
        self,
        asset: str,
        limit: int = 20,
    ) -> list[MemoryRecord]: ...

    async def search_similar(
        self,
        asset: str,
        setup_type: str,
        limit: int = 5,
    ) -> list[MemoryRecord]: ...
