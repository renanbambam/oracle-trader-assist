"""NewsAdapter — fetches financial news from newsapi.org.

Implements the NewsProvider domain protocol.
API docs: https://newsapi.org/docs/endpoints/everything
"""

from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger

from oracle.domain.market.contracts import NewsItem

_BASE_URL = "https://newsapi.org/v2/everything"
_ASSET_KEYWORD_MAP = {
    "PETR4": "Petrobras",
    "VALE3": "Vale",
    "IBOV": "Ibovespa",
    "WINFUT": "Mini Indice futuro",
    "WDOFUT": "Mini Dolar futuro",
    "EURUSD": "EUR USD",
    "XAUUSD": "Gold",
    "US100": "Nasdaq",
    "USDJPY": "USD JPY",
}


class NewsAdapter:
    """Fetches news articles from NewsAPI for a given asset."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def get_news(self, asset: str, max_results: int = 5) -> list[NewsItem]:
        if not self._api_key:
            logger.debug("NEWS_API_KEY not configured — skipping news fetch")
            return []

        keyword = _ASSET_KEYWORD_MAP.get(asset.upper(), asset)
        from_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        params = {
            "q": keyword,
            "from": from_date,
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "language": "pt",
            "apiKey": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(f"NewsAPI request failed for {asset}: {exc}")
            return []

        articles = data.get("articles") or []
        items: list[NewsItem] = []
        for art in articles[:max_results]:
            title = art.get("title") or ""
            description = art.get("description") or ""
            source = (art.get("source") or {}).get("name") or ""
            published_at = art.get("publishedAt") or ""
            if title:
                items.append(NewsItem(
                    title=title,
                    summary=description,
                    source=source,
                    published_at=published_at,
                ))

        return items
