"""FastAPI dependency injection providers.

All shared resources (DB session, Redis, EventBus) are obtained through these
functions via FastAPI's Depends() system. This is the only place that reads
from app.state — callers never access it directly.

Usage in a router:
    from oracle.interface.api.dependencies import get_db, get_event_bus

    @router.post("/trades")
    async def create_trade(
        session: AsyncSession = Depends(get_db),
        event_bus: RedisEventBus = Depends(get_event_bus),
    ):
        ...
"""

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.config.settings import Settings
from oracle.infrastructure.database.connection import build_session_factory
from oracle.infrastructure.redis.event_bus import RedisEventBus
from oracle.interface.websocket.gateway import WebSocketGateway


def get_settings(request: Request) -> Settings:
    """Return the application settings singleton."""
    return request.app.state.settings  # type: ignore[no-any-return]


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, committing on success and rolling back on error.

    The session is closed automatically after the request completes.
    """
    session_factory = build_session_factory(request.app.state.engine)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(request: Request) -> aioredis.Redis:
    """Return the shared Redis client from app state."""
    return request.app.state.redis  # type: ignore[no-any-return]


def get_event_bus(request: Request) -> RedisEventBus:
    """Return the EventBus instance from app state."""
    return request.app.state.event_bus  # type: ignore[no-any-return]


def get_ws_gateway(request: Request) -> WebSocketGateway:
    """Return the WebSocket gateway from app state."""
    return request.app.state.ws_gateway  # type: ignore[no-any-return]


async def get_record_trade_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "RecordTradeUseCase":
    from oracle.application.trade.record_trade import RecordTradeUseCase
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    repo = PostgresTradeRepository(session)
    event_bus = request.app.state.event_bus
    return RecordTradeUseCase(repository=repo, event_bus=event_bus)


async def get_close_trade_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "CloseTradeUseCase":
    from oracle.application.trade.close_trade import CloseTradeUseCase
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    repo = PostgresTradeRepository(session)
    event_bus = request.app.state.event_bus
    return CloseTradeUseCase(repository=repo, event_bus=event_bus)


async def get_load_context_use_case(
    session: AsyncSession = Depends(get_db),
) -> "LoadContextUseCase":
    from oracle.application.memory.load_context import LoadContextUseCase
    from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository

    repo = PostgresMemoryRepository(session)
    return LoadContextUseCase(repository=repo)


async def get_save_context_use_case(
    session: AsyncSession = Depends(get_db),
) -> "SaveContextUseCase":
    from oracle.application.memory.save_context import SaveContextUseCase
    from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository

    repo = PostgresMemoryRepository(session)
    return SaveContextUseCase(repository=repo)


async def get_run_analysis_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
    load_ctx: "LoadContextUseCase" = Depends(get_load_context_use_case),
    save_ctx: "SaveContextUseCase" = Depends(get_save_context_use_case),
) -> "RunAnalysisUseCase":
    from oracle.application.analysis.run_analysis import RunAnalysisUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter
    from oracle.infrastructure.database.repositories.analysis_repository import PostgresAnalysisRepository
    from oracle.infrastructure.news.calendar_adapter import CalendarAdapter
    from oracle.infrastructure.news.news_adapter import NewsAdapter

    settings = request.app.state.settings
    repo = PostgresAnalysisRepository(session)
    ai_provider = ClaudeAdapter(settings)
    event_bus = request.app.state.event_bus
    news_provider = NewsAdapter(settings.NEWS_API_KEY)
    calendar_provider = CalendarAdapter(settings.FINNHUB_API_KEY)
    return RunAnalysisUseCase(
        repository=repo,
        ai_provider=ai_provider,
        event_bus=event_bus,
        load_context_uc=load_ctx,
        save_context_uc=save_ctx,
        news_provider=news_provider,
        calendar_provider=calendar_provider,
    )


async def get_performance_use_case(
    session: AsyncSession = Depends(get_db),
) -> "GetPerformanceUseCase":
    from oracle.application.analytics.get_performance import GetPerformanceUseCase
    from oracle.infrastructure.database.repositories.analytics_repository import PostgresAnalyticsRepository
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    trade_repo = PostgresTradeRepository(session)
    analytics_repo = PostgresAnalyticsRepository(session)
    return GetPerformanceUseCase(trade_repository=trade_repo, analytics_repository=analytics_repo)


async def get_create_replay_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "CreateReplayUseCase":
    from oracle.application.replay.create_replay import CreateReplayUseCase
    from oracle.infrastructure.database.repositories.replay_repository import PostgresReplayRepository

    repo = PostgresReplayRepository(session)
    event_bus = request.app.state.event_bus
    return CreateReplayUseCase(repository=repo, event_bus=event_bus)


async def get_control_replay_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "ControlReplayUseCase":
    from oracle.application.replay.control_replay import ControlReplayUseCase
    from oracle.infrastructure.database.repositories.replay_repository import PostgresReplayRepository

    repo = PostgresReplayRepository(session)
    event_bus = request.app.state.event_bus
    return ControlReplayUseCase(repository=repo, event_bus=event_bus)


async def get_reflect_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "ReflectOnTradeUseCase":
    from oracle.application.trade.reflect_on_trade import ReflectOnTradeUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter
    from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    trade_repo = PostgresTradeRepository(session)
    memory_store = PostgresMemoryRepository(session)
    ai_provider = ClaudeAdapter(request.app.state.settings)
    event_bus = request.app.state.event_bus
    return ReflectOnTradeUseCase(
        trade_repo=trade_repo,
        memory_store=memory_store,
        ai_provider=ai_provider,
        event_bus=event_bus,
    )


def get_checklist_use_case() -> "RunChecklistUseCase":
    from oracle.application.trade.run_checklist import RunChecklistUseCase
    return RunChecklistUseCase()


async def get_search_history_use_case(
    session: AsyncSession = Depends(get_db),
) -> "SearchHistoryUseCase":
    from oracle.application.memory.search_history import SearchHistoryUseCase
    from oracle.infrastructure.database.repositories.memory_repository import PostgresMemoryRepository

    return SearchHistoryUseCase(PostgresMemoryRepository(session))


async def get_annotate_frame_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> "AnnotateFrameUseCase":
    from oracle.application.replay.annotate_frame import AnnotateFrameUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter
    from oracle.infrastructure.database.repositories.replay_repository import PostgresReplayRepository

    repo = PostgresReplayRepository(session)
    ai_provider = ClaudeAdapter(request.app.state.settings)
    event_bus = request.app.state.event_bus
    return AnnotateFrameUseCase(replay_repo=repo, ai_provider=ai_provider, event_bus=event_bus)


def get_send_message_use_case(request: Request) -> "SendMessageUseCase":
    from oracle.application.analysis.send_message import SendMessageUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter

    ai_provider = ClaudeAdapter(request.app.state.settings)
    event_bus = request.app.state.event_bus
    return SendMessageUseCase(ai_provider=ai_provider, event_bus=event_bus)


def get_market_adapter(request: Request):
    """Return a MarketDataProvider.

    Uses MT5Adapter when MT5_LOGIN is configured in settings and the
    MetaTrader5 package is available (Windows + terminal running).
    Falls back to MockMarketAdapter for Docker / Linux / offline dev.
    """
    settings = request.app.state.settings
    if settings.MT5_LOGIN:
        try:
            from oracle.infrastructure.market.mt5_adapter import MT5Adapter
            return MT5Adapter(settings)
        except (ImportError, RuntimeError):
            pass
    from oracle.infrastructure.market.mock_adapter import MockMarketAdapter
    return MockMarketAdapter()


async def get_generate_briefing_use_case(
    request: Request,
    session: AsyncSession = Depends(get_db),
    load_ctx: "LoadContextUseCase" = Depends(get_load_context_use_case),
) -> "GenerateBriefingUseCase":
    from oracle.application.briefing.generate_briefing import GenerateBriefingUseCase
    from oracle.infrastructure.ai.claude_adapter import ClaudeAdapter
    from oracle.infrastructure.database.repositories.trade_repository import PostgresTradeRepository

    trade_repo = PostgresTradeRepository(session)
    ai_provider = ClaudeAdapter(request.app.state.settings)
    return GenerateBriefingUseCase(trade_repository=trade_repo, ai_provider=ai_provider, load_context_uc=load_ctx)
