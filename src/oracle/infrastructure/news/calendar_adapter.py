"""CalendarAdapter — fetches economic calendar from Finnhub.

Implements the CalendarProvider domain protocol.
API docs: https://finnhub.io/docs/api/economic-calendar
"""

from datetime import datetime, timezone

import httpx
from loguru import logger

from oracle.domain.market.contracts import CalendarEvent

_BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

_IMPACT_MAP = {
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
}


class CalendarAdapter:
    """Fetches today's economic events from Finnhub."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def get_today_events(self) -> list[CalendarEvent]:
        if not self._api_key:
            logger.debug("FINNHUB_API_KEY not configured — skipping calendar fetch")
            return []

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params = {
            "from": today,
            "to": today,
            "token": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(f"Finnhub calendar request failed: {exc}")
            return []

        raw_events = data.get("economicCalendar") or []
        events: list[CalendarEvent] = []
        for ev in raw_events:
            impact_raw = ev.get("impact", 1)
            impact = _IMPACT_MAP.get(impact_raw, "LOW")
            events.append(CalendarEvent(
                time=ev.get("time", ""),
                title=ev.get("event", ""),
                impact=impact,
                country=ev.get("country", ""),
                actual=str(ev.get("actual", "")),
                forecast=str(ev.get("estimate", "")),
                previous=str(ev.get("prev", "")),
            ))

        return events
