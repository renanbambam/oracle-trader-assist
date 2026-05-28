"""Replay domain — contracts (protocols/interfaces)."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from oracle.domain.replay.entities import ReplaySession
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState


@runtime_checkable
class ReplayRepository(Protocol):
    """Port for persisting and querying replay sessions.

    State (current_frame, speed, ReplayState) is kept in Redis for
    performance; the full session definition is in PostgreSQL.
    """

    async def save(self, session: ReplaySession) -> ReplaySession: ...

    async def get_by_id(self, session_id: UUID) -> ReplaySession | None: ...

    async def update_state(
        self,
        session_id: UUID,
        state: ReplayState,
        current_frame: int,
        speed: PlaybackSpeed,
    ) -> None: ...

    async def get_by_asset(self, asset: str, limit: int = 10) -> list[ReplaySession]: ...

    async def save_frame_annotation(
        self,
        session_id: UUID,
        frame_index: int,
        commentary: str,
    ) -> None: ...
