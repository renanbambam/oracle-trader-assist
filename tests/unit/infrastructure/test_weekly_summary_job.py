"""Unit tests for weekly_summary_job — zero I/O, time injected as parameter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oracle.infrastructure.scheduler.jobs.weekly_summary_job import run_weekly_summary


_MONDAY_07H = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)  # Monday 08:00 BRT


def _make_settings(*, telegram_token="", telegram_chat=""):
    s = MagicMock()
    s.TELEGRAM_BOT_TOKEN = telegram_token
    s.TELEGRAM_CHAT_ID = telegram_chat
    return s


def _summary_with_trades():
    return {
        "period_start": "2026-01-01T00:00:00+00:00",
        "period_end": "2026-01-05T10:00:00+00:00",
        "trade_count": 8,
        "win_count": 5,
        "loss_count": 3,
        "win_rate": 0.625,
        "total_r": 4.5,
        "best_trade": {"r": 2.0, "asset": "PETR4", "setup": "breakout"},
        "worst_trade": {"r": -1.0, "asset": "VALE3", "setup": "reversal"},
    }


def _summary_empty():
    return {
        "period_start": "2026-01-01T00:00:00+00:00",
        "period_end": "2026-01-05T10:00:00+00:00",
        "trade_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "win_rate": 0.0,
        "total_r": 0.0,
        "best_trade": None,
        "worst_trade": None,
    }


async def test_weekly_summary_publishes_event():
    settings = _make_settings()
    event_bus = AsyncMock()
    summary = _summary_with_trades()

    with patch(
        "oracle.infrastructure.scheduler.jobs.weekly_summary_job._build_weekly_summary",
        new=AsyncMock(return_value=summary),
    ):
        await run_weekly_summary(engine=None, settings=settings, event_bus=event_bus)

    event_bus.publish.assert_awaited_once()
    call_kwargs = event_bus.publish.call_args.kwargs
    assert call_kwargs["channel"] == "system"
    assert call_kwargs["event"] == "weekly_summary.generated"
    assert call_kwargs["payload"]["trade_count"] == 8


async def test_weekly_summary_publishes_empty_when_no_trades():
    settings = _make_settings()
    event_bus = AsyncMock()

    with patch(
        "oracle.infrastructure.scheduler.jobs.weekly_summary_job._build_weekly_summary",
        new=AsyncMock(return_value=_summary_empty()),
    ):
        await run_weekly_summary(engine=None, settings=settings, event_bus=event_bus)

    payload = event_bus.publish.call_args.kwargs["payload"]
    assert payload["trade_count"] == 0
    assert payload["win_rate"] == 0.0


async def test_weekly_summary_sends_telegram_when_configured():
    settings = _make_settings(telegram_token="bot:TOKEN", telegram_chat="99")
    event_bus = AsyncMock()

    with (
        patch(
            "oracle.infrastructure.scheduler.jobs.weekly_summary_job._build_weekly_summary",
            new=AsyncMock(return_value=_summary_with_trades()),
        ),
        patch(
            "oracle.infrastructure.scheduler.jobs.weekly_summary_job._notify_telegram",
            new=AsyncMock(),
        ) as notify_mock,
    ):
        await run_weekly_summary(engine=None, settings=settings, event_bus=event_bus)

    notify_mock.assert_awaited_once()


async def test_weekly_summary_graceful_on_db_failure():
    settings = _make_settings()
    event_bus = AsyncMock()

    with patch(
        "oracle.infrastructure.scheduler.jobs.weekly_summary_job._build_weekly_summary",
        new=AsyncMock(side_effect=RuntimeError("DB unavailable")),
    ):
        await run_weekly_summary(engine=None, settings=settings, event_bus=event_bus)

    event_bus.publish.assert_not_awaited()


async def test_weekly_summary_win_rate_calculation():
    settings = _make_settings()
    event_bus = AsyncMock()
    summary = _summary_with_trades()
    assert summary["win_rate"] == pytest.approx(5 / 8, rel=1e-3)

    with patch(
        "oracle.infrastructure.scheduler.jobs.weekly_summary_job._build_weekly_summary",
        new=AsyncMock(return_value=summary),
    ):
        await run_weekly_summary(engine=None, settings=settings, event_bus=event_bus)

    payload = event_bus.publish.call_args.kwargs["payload"]
    assert payload["win_rate"] == pytest.approx(0.625)
