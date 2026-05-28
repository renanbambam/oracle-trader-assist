"""news_refresh_job — periodic background refresh of asset news.

Runs every 30 minutes during trading hours. Fetches news for the
configured BRIEFING_ASSETS and publishes a market.news_refreshed event
so connected clients can receive updates without polling.
"""

from datetime import datetime, timezone

from loguru import logger

_TRADING_HOURS_START = 9
_TRADING_HOURS_END = 18


def _is_trading_hours(now: datetime) -> bool:
    """Return True if current UTC hour falls within configured trading window."""
    brt_hour = (now.hour - 3) % 24  # UTC → BRT (UTC-3)
    return _TRADING_HOURS_START <= brt_hour < _TRADING_HOURS_END


async def run_news_refresh(
    *,
    settings,
    event_bus,
    now: datetime | None = None,
) -> None:
    """Entry point called by OracleScheduler.

    The `now` parameter is injectable for testing without mocking datetime.
    """
    current_time = now or datetime.now(timezone.utc)

    if not _is_trading_hours(current_time):
        logger.debug("NewsRefreshJob: outside trading hours — skipping")
        return

    logger.info(f"NewsRefreshJob: starting at {current_time.isoformat()}")

    if not settings.NEWS_API_KEY:
        logger.debug("NewsRefreshJob: NEWS_API_KEY not configured — skipping")
        return

    from oracle.infrastructure.news.news_adapter import NewsAdapter

    adapter = NewsAdapter(api_key=settings.NEWS_API_KEY)
    assets = settings.BRIEFING_ASSETS
    results: dict[str, list[str]] = {}

    for asset in assets:
        try:
            items = await adapter.get_news(asset, max_results=3)
            results[asset] = [item.title for item in items]
        except Exception as exc:
            logger.warning(f"NewsRefreshJob: failed for {asset} — {exc}")

    await event_bus.publish(
        channel="market",
        event="market.news_refreshed",
        payload={
            "assets": list(results.keys()),
            "refreshed_at": current_time.isoformat(),
            "counts": {asset: len(titles) for asset, titles in results.items()},
        },
    )

    total = sum(len(v) for v in results.values())
    logger.info(f"NewsRefreshJob: fetched {total} articles for {len(assets)} assets")
