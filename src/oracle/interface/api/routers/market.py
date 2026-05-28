"""Market endpoints — live quotes (mock), MT5 bridge ingest, news and calendar."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from oracle.domain.market.enums import Timeframe
from oracle.infrastructure.market.mock_adapter import MockMarketAdapter

router = APIRouter(prefix="/market", tags=["market"])


def _build_adapter():
    try:
        import yfinance  # noqa: F401
        from oracle.infrastructure.market.yahoo_adapter import YahooMarketAdapter
        return YahooMarketAdapter()
    except Exception:
        return MockMarketAdapter()


_ADAPTER = _build_adapter()

_QUOTE_SYMBOLS = ["PETR4", "VALE3", "IBOV", "WINQ", "EURUSD", "XAUUSD", "US100", "USDJPY"]
_FOREX_SYMBOLS = {"EURUSD", "XAUUSD", "US100", "USDJPY"}
_TIMEFRAMES_MTF = ["D1", "H4", "H1", "M15", "M5", "M1"]


def _session_label(symbol: str, now: datetime) -> str:
    wday = now.weekday()
    h = now.hour
    if wday >= 5:
        return "FECHADO"
    if symbol.upper() in _FOREX_SYMBOLS:
        return "REGULAR"
    if 13 <= h < 21:
        return "REGULAR"
    if h < 13:
        return "PRE"
    return "POS"


class QuoteOut(BaseModel):
    symbol: str
    price: float
    bid: float
    ask: float
    spread: float
    change_pct: float
    session: str
    is_open: bool


class IngestPayload(BaseModel):
    symbol: str
    price: float
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    volume: float | None = None
    timestamp: str | None = None


@router.get("/quotes", response_model=list[QuoteOut])
async def get_quotes() -> list[QuoteOut]:
    now = datetime.now(timezone.utc)
    quotes: list[QuoteOut] = []

    for sym in _QUOTE_SYMBOLS:
        snap = await _ADAPTER.get_snapshot(sym, Timeframe.H1)
        price = snap.current_price
        open_p = snap.current_bar.open if snap.current_bar else price
        change_pct = ((price - open_p) / open_p * 100) if open_p else 0.0
        session = _session_label(sym, now)

        quotes.append(QuoteOut(
            symbol=sym,
            price=round(price, 5),
            bid=round(snap.bid, 5),
            ask=round(snap.ask, 5),
            spread=round(snap.spread, 5),
            change_pct=round(change_pct, 3),
            session=session,
            is_open=(session == "REGULAR"),
        ))

    return quotes


@router.get("/quotes/{symbol}/timeframes")
async def get_symbol_timeframes(symbol: str) -> dict:
    sym = symbol.upper()
    mtf: dict[str, str] = {}

    for tf_str in _TIMEFRAMES_MTF:
        bars = await _ADAPTER.get_historical(sym, Timeframe(tf_str), 5)
        if len(bars) >= 2:
            first_close = bars[0].close
            last_close = bars[-1].close
            pct = ((last_close - first_close) / first_close * 100) if first_close else 0.0
            if pct > 0.3:
                trend = "BULL"
            elif pct < -0.3:
                trend = "BEAR"
            else:
                trend = "LATE"
        else:
            trend = "LATE"
        mtf[tf_str] = trend

    return {"symbol": sym, "mtf": mtf}


class NewsItemOut(BaseModel):
    title: str
    summary: str
    source: str
    published_at: str


class CalendarEventOut(BaseModel):
    time: str
    title: str
    impact: str
    country: str
    actual: str
    forecast: str
    previous: str


@router.get("/news", response_model=list[NewsItemOut])
async def get_news(
    request: Request,
    asset: str = Query(..., description="Asset ticker, e.g. PETR4"),
    limit: int = Query(5, ge=1, le=20),
) -> list[NewsItemOut]:
    settings = request.app.state.settings
    from oracle.infrastructure.news.news_adapter import NewsAdapter
    adapter = NewsAdapter(settings.NEWS_API_KEY)
    items = await adapter.get_news(asset.upper(), max_results=limit)
    return [
        NewsItemOut(
            title=it.title,
            summary=it.summary,
            source=it.source,
            published_at=it.published_at,
        )
        for it in items
    ]


@router.get("/calendar", response_model=list[CalendarEventOut])
async def get_calendar(request: Request) -> list[CalendarEventOut]:
    settings = request.app.state.settings
    from oracle.infrastructure.news.calendar_adapter import CalendarAdapter
    adapter = CalendarAdapter(settings.FINNHUB_API_KEY)
    events = await adapter.get_today_events()
    return [
        CalendarEventOut(
            time=ev.time,
            title=ev.title,
            impact=ev.impact,
            country=ev.country,
            actual=ev.actual,
            forecast=ev.forecast,
            previous=ev.previous,
        )
        for ev in events
    ]


@router.post("/ingest", status_code=200)
async def ingest_market_data(payload: IngestPayload, request: Request) -> dict:
    redis = request.app.state.redis
    event_bus = request.app.state.event_bus
    sym = payload.symbol.upper()

    record = payload.model_dump()
    record["symbol"] = sym
    record["received_at"] = datetime.now(timezone.utc).isoformat()

    await redis.set(f"market:price:{sym}", json.dumps(record))

    await event_bus.publish(
        channel="market",
        event="market.ticker_updated",
        payload={
            "symbol": sym,
            "price": payload.price,
            "bid": payload.bid,
            "ask": payload.ask,
            "spread": payload.spread,
            "change": 0.0,
        },
    )

    return {"ok": True, "symbol": sym}
