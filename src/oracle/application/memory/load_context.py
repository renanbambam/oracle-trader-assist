"""LoadContextUseCase — loads or creates a context session for an asset."""

from datetime import datetime, timezone

from oracle.application.memory.dtos import ContextOutput, LoadContextInput
from oracle.domain.memory.entities import ContextSession
from oracle.domain.memory.enums import MessageRole, SessionStatus


class LoadContextUseCase:
    def __init__(self, repository) -> None:
        self._repo = repository

    async def execute(self, data: LoadContextInput) -> ContextOutput:
        session = await self._repo.get_active_session(data.asset)
        if session is None:
            if not data.create_if_missing:
                raise ValueError(f"No active session for {data.asset}")
            session = await self._create_session(data.asset)
        return _to_output(session)

    async def get_history_for_prompt(self, asset: str, max_turns: int = 10) -> str:
        """Return recent turns formatted for injection into an analysis prompt."""
        session = await self._repo.get_active_session(asset)
        if session is None or not session.turns:
            return ""

        recent = session.turns[-max_turns:]
        lines = ["HISTÓRICO DA SESSÃO (interações recentes):"]
        for turn in recent:
            role_label = "trader" if turn.role == MessageRole.USER else "oracle"
            content = turn.content if len(turn.content) <= 300 else turn.content[:297] + "..."
            lines.append(f"[{role_label}] {content}")
        return "\n".join(lines)

    async def get_recent_records_for_prompt(self, asset: str, limit: int = 3) -> str:
        """Return recent MemoryRecords formatted for prompt injection."""
        records = await self._repo.get_records_by_asset(asset, limit=limit)
        if not records:
            return ""
        lines = [f"MEMÓRIA ANTERIOR ({asset}):"]
        for r in records:
            snippet = r.content[:200] + "..." if len(r.content) > 200 else r.content
            lines.append(f"- [{r.setup_type}] {snippet}")
        return "\n".join(lines)

    async def _create_session(self, asset: str) -> ContextSession:
        now = datetime.now(timezone.utc)
        session = ContextSession(
            asset=asset,
            status=SessionStatus.ACTIVE,
            started_at=now,
            last_active_at=now,
        )
        return await self._repo.save_session(session)


def _to_output(session: ContextSession) -> ContextOutput:
    budget = session.token_budget
    usage_pct = round(session.token_count / budget.max_total * 100, 1) if budget.max_total else 0.0
    return ContextOutput(
        session_id=session.id,
        asset=session.asset,
        status=session.status,
        token_count=session.token_count,
        turn_count=session.turn_count,
        usage_pct=usage_pct,
        last_active_at=session.last_active_at,
    )
