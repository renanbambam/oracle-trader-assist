"""Integration tests for PostgresReplayRepository — real PostgreSQL."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from oracle.domain.market.enums import Timeframe
from oracle.domain.replay.entities import ReplaySession
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState
from oracle.domain.replay.value_objects import TimeRange
from oracle.infrastructure.database.repositories.replay_repository import PostgresReplayRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker

_START = datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc)
_END = datetime(2024, 6, 1, 17, 30, tzinfo=timezone.utc)


def _session(**overrides) -> ReplaySession:
    defaults = dict(
        asset="PETR4",
        timeframe=Timeframe.M5,
        range=TimeRange(start=_START, end=_END),
        state=ReplayState.IDLE,
        total_frames=10,
    )
    return ReplaySession(**{**defaults, **overrides})


async def test_save_and_get_by_id(session):
    repo = PostgresReplayRepository(session)
    s = _session()

    await repo.save(s)
    found = await repo.get_by_id(s.id)

    assert found is not None
    assert found.id == s.id
    assert found.asset == "PETR4"
    assert found.timeframe == Timeframe.M5
    assert found.state == ReplayState.IDLE
    assert found.total_frames == 10


async def test_get_by_id_not_found_returns_none(session):
    repo = PostgresReplayRepository(session)
    assert await repo.get_by_id(uuid4()) is None


async def test_time_range_roundtrip(session):
    repo = PostgresReplayRepository(session)
    s = _session()

    await repo.save(s)
    found = await repo.get_by_id(s.id)

    assert found.range.start.replace(tzinfo=timezone.utc) == _START or found.range.start == _START
    assert found.range.end.replace(tzinfo=timezone.utc) == _END or found.range.end == _END


async def test_update_state(session):
    repo = PostgresReplayRepository(session)
    s = _session(total_frames=20)
    await repo.save(s)

    await repo.update_state(s.id, ReplayState.PLAYING, 5, PlaybackSpeed.X2)
    found = await repo.get_by_id(s.id)

    assert found.state == ReplayState.PLAYING
    assert found.current_frame == 5
    assert found.speed == PlaybackSpeed.X2


async def test_update_state_to_completed(session):
    repo = PostgresReplayRepository(session)
    s = _session(total_frames=5)
    await repo.save(s)

    await repo.update_state(s.id, ReplayState.COMPLETED, 4, PlaybackSpeed.X1)
    found = await repo.get_by_id(s.id)

    assert found.state == ReplayState.COMPLETED
    assert found.current_frame == 4


async def test_get_by_asset(session):
    repo = PostgresReplayRepository(session)
    petr = _session(asset="PETR4")
    win = _session(asset="WINFUT")
    await repo.save(petr)
    await repo.save(win)

    results = await repo.get_by_asset("PETR4")
    assert all(r.asset == "PETR4" for r in results)
    assert any(r.id == petr.id for r in results)


async def test_enum_roundtrip(session):
    repo = PostgresReplayRepository(session)
    s = _session(speed=PlaybackSpeed.X5, state=ReplayState.PAUSED)
    await repo.save(s)

    found = await repo.get_by_id(s.id)
    assert found.speed == PlaybackSpeed.X5
    assert found.state == ReplayState.PAUSED
