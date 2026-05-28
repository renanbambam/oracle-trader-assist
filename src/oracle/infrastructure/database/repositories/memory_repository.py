"""PostgreSQL implementation of MemoryStore."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.domain.memory.entities import ChatMessage, ContextSession, MemoryRecord
from oracle.domain.memory.enums import MessageRole, SessionStatus, TrimStrategy
from oracle.domain.memory.value_objects import TokenBudget
from oracle.infrastructure.database.models.memory_model import ContextSessionOrm, MemoryRecordOrm


def _session_to_orm(s: ContextSession) -> ContextSessionOrm:
    turns_raw = [
        {
            "id": str(t.id),
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "session_id": str(t.session_id),
            "role": str(t.role),
            "content": t.content,
            "token_count": t.token_count,
            "analysis_id": str(t.analysis_id) if t.analysis_id else None,
        }
        for t in s.turns
    ]
    return ContextSessionOrm(
        id=s.id,
        created_at=s.created_at,
        updated_at=s.updated_at,
        asset=s.asset,
        status=str(s.status),
        token_count=s.token_count,
        turns_json=json.dumps(turns_raw) if turns_raw else None,
        trim_strategy=str(s.trim_strategy),
        started_at=s.started_at,
        last_active_at=s.last_active_at,
    )


def _session_to_domain(row: ContextSessionOrm) -> ContextSession:
    turns: list[ChatMessage] = []
    if row.turns_json:
        for d in json.loads(row.turns_json):
            turns.append(
                ChatMessage(
                    id=d["id"],
                    created_at=d["created_at"],
                    updated_at=d["updated_at"],
                    session_id=d["session_id"],
                    role=MessageRole(d["role"]),
                    content=d["content"],
                    token_count=d.get("token_count"),
                    analysis_id=d.get("analysis_id"),
                )
            )
    return ContextSession(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        asset=row.asset,
        status=SessionStatus(row.status),
        token_count=row.token_count,
        turns=turns,
        token_budget=TokenBudget(),
        trim_strategy=TrimStrategy(row.trim_strategy),
        started_at=row.started_at,
        last_active_at=row.last_active_at,
    )


def _record_to_orm(r: MemoryRecord) -> MemoryRecordOrm:
    return MemoryRecordOrm(
        id=r.id,
        created_at=r.created_at,
        updated_at=r.updated_at,
        asset=r.asset,
        setup_type=r.setup_type,
        content=r.content,
        source_analysis_id=r.source_analysis_id,
        source_trade_id=r.source_trade_id,
        relevance_score=r.relevance_score,
    )


def _record_to_domain(row: MemoryRecordOrm) -> MemoryRecord:
    return MemoryRecord(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        asset=row.asset,
        setup_type=row.setup_type,
        content=row.content,
        source_analysis_id=row.source_analysis_id,
        source_trade_id=row.source_trade_id,
        relevance_score=row.relevance_score,
    )


class PostgresMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_session(self, session: ContextSession) -> ContextSession:
        self._session.add(_session_to_orm(session))
        await self._session.flush()
        return session

    async def get_session(self, session_id: UUID) -> ContextSession | None:
        row = await self._session.get(ContextSessionOrm, session_id)
        return _session_to_domain(row) if row else None

    async def get_active_session(self, asset: str) -> ContextSession | None:
        stmt = (
            select(ContextSessionOrm)
            .where(
                ContextSessionOrm.asset == asset,
                ContextSessionOrm.status == SessionStatus.ACTIVE,
            )
            .order_by(ContextSessionOrm.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalars().first()
        return _session_to_domain(row) if row else None

    async def update_session(self, session: ContextSession) -> ContextSession:
        await self._session.merge(_session_to_orm(session))
        await self._session.flush()
        return session

    async def expire_session(self, session_id: UUID) -> None:
        row = await self._session.get(ContextSessionOrm, session_id)
        if row:
            row.status = SessionStatus.EXPIRED
            await self._session.flush()

    async def save_record(self, record: MemoryRecord) -> MemoryRecord:
        self._session.add(_record_to_orm(record))
        await self._session.flush()
        return record

    async def get_records_by_asset(self, asset: str, limit: int = 20) -> list[MemoryRecord]:
        stmt = (
            select(MemoryRecordOrm)
            .where(MemoryRecordOrm.asset == asset)
            .order_by(MemoryRecordOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_record_to_domain(r) for r in rows]

    async def search_similar(self, asset: str, setup_type: str, limit: int = 5) -> list[MemoryRecord]:
        stmt = (
            select(MemoryRecordOrm)
            .where(
                MemoryRecordOrm.asset == asset,
                MemoryRecordOrm.setup_type == setup_type,
            )
            .order_by(MemoryRecordOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_record_to_domain(r) for r in rows]
