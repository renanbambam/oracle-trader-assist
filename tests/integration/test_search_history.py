"""Integration tests for SearchHistoryUseCase — real PostgreSQL."""

import pytest

from oracle.application.memory.dtos import SearchHistoryInput
from oracle.application.memory.search_history import SearchHistoryUseCase
from oracle.domain.memory.entities import MemoryRecord
from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


async def test_search_history_returns_matching_records(session):
    repo = PostgresMemoryRepository(session)

    record = MemoryRecord(
        asset="PETR4",
        setup_type="breakout",
        content="Rompimento de resistência com volume acima da média.",
    )
    await repo.save_record(record)

    use_case = SearchHistoryUseCase(repo)
    result = await use_case.execute(SearchHistoryInput(asset="PETR4", setup_type="breakout"))

    assert any(r.id == record.id for r in result.records)
    assert result.prompt_context != ""
    assert "breakout" in result.prompt_context.lower() or "PETR4" in result.prompt_context


async def test_search_history_no_match_returns_empty(session):
    repo = PostgresMemoryRepository(session)
    use_case = SearchHistoryUseCase(repo)

    result = await use_case.execute(
        SearchHistoryInput(asset="XYZXYZ", setup_type="nonexistent_setup_xyz")
    )

    assert result.records == []
    assert result.prompt_context == ""


async def test_search_history_respects_limit(session):
    repo = PostgresMemoryRepository(session)

    for i in range(4):
        await repo.save_record(
            MemoryRecord(asset="VALE3", setup_type="reversal", content=f"Reversão #{i}")
        )

    use_case = SearchHistoryUseCase(repo)
    result = await use_case.execute(
        SearchHistoryInput(asset="VALE3", setup_type="reversal", limit=2)
    )

    assert len(result.records) <= 2
