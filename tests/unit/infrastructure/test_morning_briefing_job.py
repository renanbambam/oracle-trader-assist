"""Unit tests for morning_briefing_job — zero I/O, injectable clock."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oracle.infrastructure.scheduler.jobs.morning_briefing_job import run_morning_briefing


def _make_settings(*, telegram_token="", telegram_chat="", assets=None):
    s = MagicMock()
    s.TELEGRAM_BOT_TOKEN = telegram_token
    s.TELEGRAM_CHAT_ID = telegram_chat
    s.BRIEFING_ASSETS = assets or ["PETR4", "VALE3"]
    s.ANTHROPIC_API_KEY = "fake-key"
    return s


def _make_briefing_output(content="Análise do dia"):
    from oracle.application.briefing.dtos import BriefingOutput
    return BriefingOutput(
        content=content,
        assets_covered=["PETR4", "VALE3"],
        key_levels={},
        upcoming_events=[],
        recent_trade_context="Nenhum trade.",
        generated_at=datetime(2026, 1, 6, 7, 0, tzinfo=timezone.utc),
    )


async def test_morning_briefing_publishes_event():
    settings = _make_settings()
    event_bus = AsyncMock()
    briefing_output = _make_briefing_output()

    with patch(
        "oracle.infrastructure.scheduler.jobs.morning_briefing_job._generate_briefing",
        new=AsyncMock(return_value=briefing_output),
    ):
        await run_morning_briefing(engine=None, settings=settings, event_bus=event_bus)

    event_bus.publish.assert_awaited_once()
    call_kwargs = event_bus.publish.call_args.kwargs
    assert call_kwargs["channel"] == "system"
    assert call_kwargs["event"] == "briefing.generated"
    assert "content" in call_kwargs["payload"]
    assert "assets" in call_kwargs["payload"]


async def test_morning_briefing_sends_telegram_when_configured():
    settings = _make_settings(telegram_token="bot:TOKEN", telegram_chat="12345")
    event_bus = AsyncMock()
    briefing_output = _make_briefing_output()

    telegram_mock = AsyncMock(return_value=True)

    with (
        patch(
            "oracle.infrastructure.scheduler.jobs.morning_briefing_job._generate_briefing",
            new=AsyncMock(return_value=briefing_output),
        ),
        patch(
            "oracle.infrastructure.scheduler.jobs.morning_briefing_job._notify_telegram",
            new=AsyncMock(),
        ) as notify_mock,
    ):
        await run_morning_briefing(engine=None, settings=settings, event_bus=event_bus)

    notify_mock.assert_awaited_once()


async def test_morning_briefing_skips_telegram_when_unconfigured():
    settings = _make_settings()  # empty token
    event_bus = AsyncMock()
    briefing_output = _make_briefing_output()

    with (
        patch(
            "oracle.infrastructure.scheduler.jobs.morning_briefing_job._generate_briefing",
            new=AsyncMock(return_value=briefing_output),
        ),
        patch(
            "oracle.infrastructure.messaging.telegram_adapter.TelegramAdapter.send_message",
            new_callable=AsyncMock,
        ) as send_mock,
    ):
        await run_morning_briefing(engine=None, settings=settings, event_bus=event_bus)

    send_mock.assert_not_awaited()


async def test_morning_briefing_handles_generation_failure_gracefully():
    settings = _make_settings()
    event_bus = AsyncMock()

    with patch(
        "oracle.infrastructure.scheduler.jobs.morning_briefing_job._generate_briefing",
        new=AsyncMock(side_effect=RuntimeError("AI unavailable")),
    ):
        await run_morning_briefing(engine=None, settings=settings, event_bus=event_bus)

    event_bus.publish.assert_not_awaited()


async def test_morning_briefing_payload_content_is_truncated_to_500():
    settings = _make_settings()
    event_bus = AsyncMock()
    long_content = "A" * 2000
    briefing_output = _make_briefing_output(content=long_content)

    with patch(
        "oracle.infrastructure.scheduler.jobs.morning_briefing_job._generate_briefing",
        new=AsyncMock(return_value=briefing_output),
    ):
        await run_morning_briefing(engine=None, settings=settings, event_bus=event_bus)

    payload = event_bus.publish.call_args.kwargs["payload"]
    assert len(payload["content"]) <= 500
