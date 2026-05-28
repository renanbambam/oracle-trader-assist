"""Integration tests for AnnotateFrameUseCase — real PostgreSQL, fake AI."""

from datetime import datetime, timezone

import pytest

from oracle.application.replay.annotate_frame import AnnotateFrameUseCase
from oracle.application.replay.create_replay import CreateReplayUseCase
from oracle.application.replay.dtos import AnnotateFrameInput, CreateReplayInput
from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.database.repositories.replay_repository import PostgresReplayRepository
from tests.integration.conftest import requires_docker

pytestmark = requires_docker


class FakeAIProvider:
    async def complete(self, prompt: str, system: str, image_b64=None) -> str:
        return "Candle de indecisão após movimento de alta. Aguardar confirmação direcional."

    async def stream_message(self, message, system):
        yield "token"

    async def stream(self, messages, system):
        yield "token"

    async def count_tokens(self, text: str) -> int:
        return len(text.split())


class FakeEventBus:
    def __init__(self):
        self.published = []

    async def publish(self, channel, event, payload):
        self.published.append((channel, event, payload))

    def subscribe(self, channels):
        return iter([])


async def test_annotate_frame_saves_commentary(session):
    repo = PostgresReplayRepository(session)
    service = CreateReplayUseCase(repository=repo, event_bus=FakeEventBus())

    status = await service.execute(
        CreateReplayInput(
            asset="PETR4",
            timeframe=Timeframe.M5,
            start=datetime(2024, 1, 2, 9, 0, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, 11, 0, tzinfo=timezone.utc),
        )
    )
    session_id = status.session_id

    use_case = AnnotateFrameUseCase(
        replay_repo=repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )

    result = await use_case.execute(session_id, AnnotateFrameInput(frame_index=0))

    assert result.session_id == session_id
    assert result.frame_index == 0
    assert "Candle" in result.commentary or len(result.commentary) > 5


async def test_annotate_frame_persists_to_db(session):
    repo = PostgresReplayRepository(session)
    service = CreateReplayUseCase(repository=repo, event_bus=FakeEventBus())

    status = await service.execute(
        CreateReplayInput(
            asset="VALE3",
            timeframe=Timeframe.M15,
            start=datetime(2024, 3, 1, 9, 0, tzinfo=timezone.utc),
            end=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
    )

    use_case = AnnotateFrameUseCase(
        replay_repo=repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )
    await use_case.execute(status.session_id, AnnotateFrameInput(frame_index=0))

    reloaded = await repo.get_by_id(status.session_id)
    assert reloaded is not None
    assert reloaded.frames[0].ai_commentary is not None


async def test_annotate_frame_invalid_index_raises(session):
    repo = PostgresReplayRepository(session)
    service = CreateReplayUseCase(repository=repo, event_bus=FakeEventBus())

    status = await service.execute(
        CreateReplayInput(
            asset="WINFUT",
            timeframe=Timeframe.M5,
            start=datetime(2024, 6, 1, 9, 0, tzinfo=timezone.utc),
            end=datetime(2024, 6, 1, 9, 30, tzinfo=timezone.utc),
        )
    )

    use_case = AnnotateFrameUseCase(
        replay_repo=repo,
        ai_provider=FakeAIProvider(),
        event_bus=FakeEventBus(),
    )

    with pytest.raises(ValueError, match="out of range"):
        await use_case.execute(status.session_id, AnnotateFrameInput(frame_index=9999))
