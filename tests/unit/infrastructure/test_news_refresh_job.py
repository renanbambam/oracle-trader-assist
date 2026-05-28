"""Unit tests for news_refresh_job — time injected via `now` parameter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oracle.infrastructure.scheduler.jobs.news_refresh_job import (
    _is_trading_hours,
    run_news_refresh,
)


# ── _is_trading_hours helper ─────────────────────────────────────────────────

@pytest.mark.parametrize("utc_hour, expected", [
    (12, True),   # 09:00 BRT — open
    (15, True),   # 12:00 BRT — open
    (20, True),   # 17:00 BRT — open
    (21, False),  # 18:00 BRT — closed
    (9, False),   # 06:00 BRT — before open
    (23, False),  # 20:00 BRT — after close
])
def test_is_trading_hours(utc_hour, expected):
    now = datetime(2026, 1, 5, utc_hour, 0, tzinfo=timezone.utc)
    assert _is_trading_hours(now) is expected


# ── run_news_refresh ─────────────────────────────────────────────────────────

def _make_settings(*, api_key="test-key", assets=None):
    s = MagicMock()
    s.NEWS_API_KEY = api_key
    s.BRIEFING_ASSETS = assets or ["PETR4", "VALE3"]
    return s


_TRADING_TIME = datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc)  # 10:00 BRT
_CLOSED_TIME = datetime(2026, 1, 5, 23, 0, tzinfo=timezone.utc)   # 20:00 BRT


async def test_news_refresh_publishes_event_during_trading_hours():
    settings = _make_settings()
    event_bus = AsyncMock()

    from oracle.domain.market.contracts import NewsItem
    fake_items = [NewsItem(title="PETR4 sobe", summary="", source="Info", published_at="2026-01-05")]

    with patch(
        "oracle.infrastructure.news.news_adapter.NewsAdapter"
    ) as MockAdapter:
        MockAdapter.return_value.get_news = AsyncMock(return_value=fake_items)
        await run_news_refresh(settings=settings, event_bus=event_bus, now=_TRADING_TIME)

    event_bus.publish.assert_awaited_once()
    call_kwargs = event_bus.publish.call_args.kwargs
    assert call_kwargs["channel"] == "market"
    assert call_kwargs["event"] == "market.news_refreshed"
    assert "PETR4" in call_kwargs["payload"]["assets"]


async def test_news_refresh_skips_outside_trading_hours():
    settings = _make_settings()
    event_bus = AsyncMock()

    await run_news_refresh(settings=settings, event_bus=event_bus, now=_CLOSED_TIME)

    event_bus.publish.assert_not_awaited()


async def test_news_refresh_skips_when_api_key_missing():
    settings = _make_settings(api_key="")
    event_bus = AsyncMock()

    await run_news_refresh(settings=settings, event_bus=event_bus, now=_TRADING_TIME)

    event_bus.publish.assert_not_awaited()


async def test_news_refresh_handles_partial_failures():
    settings = _make_settings()
    event_bus = AsyncMock()

    from oracle.domain.market.contracts import NewsItem
    fake_items = [NewsItem(title="VALE3 cai", summary="", source="x", published_at="2026-01-05")]

    def _get_news_side_effect(asset, max_results=3):
        if asset == "PETR4":
            raise RuntimeError("API timeout")
        return fake_items

    with patch(
        "oracle.infrastructure.news.news_adapter.NewsAdapter"
    ) as MockAdapter:
        MockAdapter.return_value.get_news = AsyncMock(side_effect=_get_news_side_effect)
        await run_news_refresh(settings=settings, event_bus=event_bus, now=_TRADING_TIME)

    # Still publishes — partial results are acceptable
    event_bus.publish.assert_awaited_once()
    payload = event_bus.publish.call_args.kwargs["payload"]
    assert "VALE3" in payload["assets"]


async def test_news_refresh_payload_contains_counts():
    settings = _make_settings(assets=["PETR4"])
    event_bus = AsyncMock()

    from oracle.domain.market.contracts import NewsItem
    fake_items = [
        NewsItem(title="N1", summary="", source="s", published_at=""),
        NewsItem(title="N2", summary="", source="s", published_at=""),
    ]

    with patch(
        "oracle.infrastructure.news.news_adapter.NewsAdapter"
    ) as MockAdapter:
        MockAdapter.return_value.get_news = AsyncMock(return_value=fake_items)
        await run_news_refresh(settings=settings, event_bus=event_bus, now=_TRADING_TIME)

    payload = event_bus.publish.call_args.kwargs["payload"]
    assert payload["counts"]["PETR4"] == 2
