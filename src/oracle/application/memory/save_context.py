"""SaveContextUseCase — appends messages and manages session lifecycle."""

from datetime import datetime, timezone
from uuid import UUID

from oracle.application.memory.dtos import AppendMessageInput, ContextOutput
from oracle.application.memory.load_context import _to_output
from oracle.domain.memory.entities import ChatMessage


class SaveContextUseCase:
    def __init__(self, repository) -> None:
        self._repo = repository

    async def execute(self, data: AppendMessageInput) -> ContextOutput:
        """Append a message to the given session and return updated output."""
        session = await self._repo.get_session(data.session_id)
        if session is None:
            raise ValueError(f"Session {data.session_id} not found")

        now = datetime.now(timezone.utc)
        msg = ChatMessage(
            session_id=data.session_id,
            role=data.role,
            content=data.content,
        )
        session.turns.append(msg)
        session.token_count += len(data.content.split())  # rough approximation
        session.last_active_at = now
        session.updated_at = now

        await self._repo.update_session(session)
        return _to_output(session)

    async def expire(self, session_id: UUID) -> None:
        await self._repo.expire_session(session_id)
