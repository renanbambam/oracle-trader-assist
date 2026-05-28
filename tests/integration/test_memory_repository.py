"""Integration tests for PostgresMemoryRepository — real PostgreSQL."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from oracle.domain.memory.entities import ChatMessage, ContextSession, MemoryRecord
from oracle.domain.memory.enums import MessageRole, SessionStatus
from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session(**overrides) -> ContextSession:
    now = _now()
    defaults = dict(asset="PETR4", started_at=now, last_active_at=now)
    return ContextSession(**{**defaults, **overrides})


def _record(**overrides) -> MemoryRecord:
    defaults = dict(asset="PETR4", setup_type="breakout", content="Rompimento na abertura com gap de alta.")
    return MemoryRecord(**{**defaults, **overrides})


async def test_save_session_and_get_by_id(session):
    repo = PostgresMemoryRepository(session)
    s = _session()

    await repo.save_session(s)
    found = await repo.get_session(s.id)

    assert found is not None
    assert found.id == s.id
    assert found.asset == "PETR4"
    assert found.status == SessionStatus.ACTIVE


async def test_get_session_not_found_returns_none(session):
    repo = PostgresMemoryRepository(session)
    assert await repo.get_session(uuid4()) is None


async def test_get_active_session_by_asset(session):
    repo = PostgresMemoryRepository(session)
    s = _session(asset="WINFUT")
    await repo.save_session(s)

    found = await repo.get_active_session("WINFUT")
    assert found is not None
    assert found.id == s.id


async def test_get_active_session_ignores_expired(session):
    repo = PostgresMemoryRepository(session)
    expired = _session(asset="VALE3", status=SessionStatus.EXPIRED)
    await repo.save_session(expired)

    found = await repo.get_active_session("VALE3")
    assert found is None


async def test_expire_session(session):
    repo = PostgresMemoryRepository(session)
    s = _session()
    await repo.save_session(s)

    await repo.expire_session(s.id)
    found = await repo.get_session(s.id)
    assert found.status == SessionStatus.EXPIRED


async def test_turns_roundtrip(session):
    repo = PostgresMemoryRepository(session)
    s = _session()
    msg = ChatMessage(session_id=s.id, role=MessageRole.USER, content="Analise PETR4 M5")
    s.turns.append(msg)

    await repo.save_session(s)
    found = await repo.get_session(s.id)

    assert len(found.turns) == 1
    assert found.turns[0].role == MessageRole.USER
    assert found.turns[0].content == "Analise PETR4 M5"


async def test_save_record_and_get_by_asset(session):
    repo = PostgresMemoryRepository(session)
    r = _record()
    await repo.save_record(r)

    records = await repo.get_records_by_asset("PETR4")
    assert any(rec.id == r.id for rec in records)
    assert all(rec.asset == "PETR4" for rec in records)


async def test_search_similar_filters_setup_type(session):
    repo = PostgresMemoryRepository(session)
    breakout = _record(setup_type="breakout")
    reversal = _record(setup_type="reversal")
    await repo.save_record(breakout)
    await repo.save_record(reversal)

    results = await repo.search_similar("PETR4", "breakout")
    setup_types = {r.setup_type for r in results}
    assert "breakout" in setup_types
    assert "reversal" not in setup_types
