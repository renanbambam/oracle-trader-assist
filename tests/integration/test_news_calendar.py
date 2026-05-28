"""Integration tests for NewsAdapter and CalendarAdapter — mocked HTTP responses."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oracle.infrastructure.news.news_adapter import NewsAdapter
from oracle.infrastructure.news.calendar_adapter import CalendarAdapter


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _patch_httpx(json_data: dict):
    """Context manager that patches httpx.AsyncClient.get to return json_data."""
    mock_resp = _mock_response(json_data)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch("httpx.AsyncClient", return_value=mock_ctx)


@pytest.fixture()
def news_api_response():
    return {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "title": "Petrobras anuncia dividendos recordes",
                "description": "A companhia informou distribuição de R$ 4,00 por ação.",
                "source": {"id": "uol", "name": "UOL"},
                "publishedAt": "2024-01-02T10:00:00Z",
            },
            {
                "title": "PETR4 atinge máxima histórica",
                "description": "Ação sobe 3% após resultado trimestral.",
                "source": {"id": None, "name": "InfoMoney"},
                "publishedAt": "2024-01-02T09:00:00Z",
            },
        ],
    }


@pytest.fixture()
def finnhub_calendar_response():
    return {
        "economicCalendar": [
            {
                "time": "2024-01-02T14:30:00+00:00",
                "event": "US Non-Farm Payrolls",
                "impact": 3,
                "country": "US",
                "actual": "200K",
                "estimate": "180K",
                "prev": "170K",
            },
            {
                "time": "2024-01-02T12:00:00+00:00",
                "event": "ECB Rate Decision",
                "impact": 2,
                "country": "EU",
                "actual": "",
                "estimate": "4.5%",
                "prev": "4.5%",
            },
            {
                "time": "2024-01-02T09:00:00+00:00",
                "event": "Brazil CPI",
                "impact": 1,
                "country": "BR",
                "actual": "4.6%",
                "estimate": "4.5%",
                "prev": "4.3%",
            },
        ]
    }


async def test_news_adapter_returns_items(news_api_response):
    adapter = NewsAdapter(api_key="test-key")
    with _patch_httpx(news_api_response):
        items = await adapter.get_news("PETR4", max_results=5)

    assert len(items) == 2
    assert items[0].title == "Petrobras anuncia dividendos recordes"
    assert items[0].source == "UOL"
    assert items[0].published_at == "2024-01-02T10:00:00Z"


async def test_news_adapter_empty_key_returns_empty():
    adapter = NewsAdapter(api_key="")
    items = await adapter.get_news("PETR4")
    assert items == []


async def test_news_adapter_respects_max_results(news_api_response):
    adapter = NewsAdapter(api_key="test-key")
    with _patch_httpx(news_api_response):
        items = await adapter.get_news("PETR4", max_results=1)

    assert len(items) <= 1


async def test_news_adapter_handles_http_error():
    adapter = NewsAdapter(api_key="test-key")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_ctx):
        items = await adapter.get_news("PETR4")
    assert items == []


async def test_calendar_adapter_returns_events(finnhub_calendar_response):
    adapter = CalendarAdapter(api_key="test-key")
    with _patch_httpx(finnhub_calendar_response):
        events = await adapter.get_today_events()

    assert len(events) == 3
    high = [e for e in events if e.impact == "HIGH"]
    medium = [e for e in events if e.impact == "MEDIUM"]
    low = [e for e in events if e.impact == "LOW"]
    assert len(high) == 1
    assert len(medium) == 1
    assert len(low) == 1
    assert high[0].title == "US Non-Farm Payrolls"
    assert high[0].country == "US"


async def test_calendar_adapter_empty_key_returns_empty():
    adapter = CalendarAdapter(api_key="")
    events = await adapter.get_today_events()
    assert events == []


async def test_calendar_adapter_empty_response():
    adapter = CalendarAdapter(api_key="test-key")
    with _patch_httpx({"economicCalendar": []}):
        events = await adapter.get_today_events()
    assert events == []


async def test_calendar_adapter_handles_http_error():
    adapter = CalendarAdapter(api_key="test-key")
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("timeout"))
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", return_value=mock_ctx):
        events = await adapter.get_today_events()
    assert events == []
