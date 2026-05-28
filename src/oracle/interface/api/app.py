"""FastAPI application factory.

Using a factory function (create_app) instead of a module-level app instance:
- Enables passing custom Settings for tests without monkeypatching env vars
- Makes the startup/shutdown lifecycle explicit and testable
- Avoids circular import issues with dependencies

Lifespan sequence:
  startup:  setup logging → create DB engine → create Redis client →
            create EventBus → create WS gateway → start broadcaster task
  shutdown: cancel broadcaster → close Redis → dispose DB engine
"""

import asyncio
import pathlib
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from oracle.config.settings import Settings, get_settings
from oracle.core.logging import setup_logging
from oracle.infrastructure.database.connection import build_engine, build_session_factory
from oracle.infrastructure.redis.client import build_redis_client
from oracle.infrastructure.redis.event_bus import RedisEventBus
from oracle.interface.api.middleware import CorrelationIdMiddleware, RequestLoggingMiddleware
from oracle.interface.api.routers import analyses, analytics, briefing, chat, health, market, memory, replay, trades
from oracle.interface.websocket.broadcaster import EventBroadcaster
from oracle.interface.websocket.cold_start import make_snapshot_provider
from oracle.interface.websocket.gateway import WebSocketGateway, router as ws_router


def _build_and_start_scheduler(*, settings, engine, event_bus):
    """Create, register jobs, and start the OracleScheduler."""
    from oracle.infrastructure.scheduler.scheduler import OracleScheduler
    from oracle.infrastructure.scheduler.jobs.morning_briefing_job import run_morning_briefing
    from oracle.infrastructure.scheduler.jobs.weekly_summary_job import run_weekly_summary
    from oracle.infrastructure.scheduler.jobs.news_refresh_job import run_news_refresh

    shared = {"engine": engine, "settings": settings, "event_bus": event_bus}

    scheduler = OracleScheduler(
        redis_url=settings.redis_url,
        timezone=settings.SCHEDULER_TIMEZONE,
    )

    scheduler.add_cron_job(
        run_morning_briefing,
        job_id="oracle_morning_briefing",
        day_of_week="mon-fri",
        hour=7,
        minute=0,
        kwargs=shared,
    )

    scheduler.add_cron_job(
        run_weekly_summary,
        job_id="oracle_weekly_summary",
        day_of_week="mon",
        hour=8,
        minute=0,
        kwargs=shared,
    )

    scheduler.add_interval_job(
        run_news_refresh,
        job_id="oracle_news_refresh",
        minutes=30,
        kwargs={"settings": settings, "event_bus": event_bus},
    )

    scheduler.start()
    return scheduler


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Override settings (useful in tests). Defaults to get_settings().

    Returns:
        Configured FastAPI application ready to serve requests.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(level=settings.LOG_LEVEL, serialize=settings.LOG_SERIALIZE)

    # Build shared infrastructure resources
    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    redis_client = build_redis_client(settings)
    event_bus = RedisEventBus(redis_client)
    ws_gateway = WebSocketGateway(
        max_connections=settings.WS_MAX_CONNECTIONS,
        snapshot_provider=make_snapshot_provider(engine) if settings.ENVIRONMENT != "test" else None,
    )
    broadcaster = EventBroadcaster(event_bus=event_bus, gateway=ws_gateway)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # ── Startup ───────────────────────────────────────────────────────────
        if settings.ENVIRONMENT != "test":
            _alembic_ini = pathlib.Path(__file__).resolve().parents[4] / "alembic.ini"
            if _alembic_ini.exists():
                from alembic import command as _alembic_cmd
                from alembic.config import Config as _AlembicConfig
                _cfg = _AlembicConfig(str(_alembic_ini))
                await asyncio.get_running_loop().run_in_executor(
                    None, _alembic_cmd.upgrade, _cfg, "head"
                )
                logger.info("Database migrations applied (alembic upgrade head)")

        # Store resources in app.state — accessible via FastAPI Depends
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.redis = redis_client
        app.state.event_bus = event_bus
        app.state.ws_gateway = ws_gateway

        # Broadcaster runs as a background task — routes Redis events to WS clients.
        # Skipped in test environment: Redis is unavailable and TCP connection
        # attempts cause long teardown delays that exceed the lifespan timeout.
        broadcaster_task: asyncio.Task | None = None
        if settings.ENVIRONMENT != "test":
            broadcaster_task = asyncio.create_task(broadcaster.run())

        # Scheduler — APScheduler with Redis jobstore.
        # Skipped in test environment (no Redis + no real AI calls needed).
        scheduler = None
        if settings.ENVIRONMENT != "test" and settings.SCHEDULER_ENABLED:
            try:
                scheduler = _build_and_start_scheduler(
                    settings=settings,
                    engine=engine,
                    event_bus=event_bus,
                )
            except Exception:
                traceback.print_exc()  # bypass loguru queue — always visible
                logger.exception("Scheduler failed to start — continuing without scheduler")

        logger.info(
            f"{settings.APP_NAME} v{settings.APP_VERSION} started "
            f"[{settings.ENVIRONMENT}]"
        )
        yield

        # ── Shutdown ──────────────────────────────────────────────────────────
        if scheduler is not None:
            scheduler.shutdown()

        if broadcaster_task is not None:
            broadcaster_task.cancel()
            try:
                await broadcaster_task
            except asyncio.CancelledError:
                pass

        await redis_client.aclose()
        await engine.dispose()
        logger.info(f"{settings.APP_NAME} stopped")

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Oracle Trader Assist — AI-powered trading intelligence platform. "
            "Persistent context, realtime analysis, decision support."
        ),
        # Disable interactive docs in production
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Middleware (registered in reverse execution order) ────────────────────
    # Execution order: CORSMiddleware → CorrelationIdMiddleware → RequestLogging
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix=settings.API_V1_PREFIX)
    app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
    app.include_router(trades.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analyses.router, prefix=settings.API_V1_PREFIX)
    app.include_router(memory.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
    app.include_router(replay.router, prefix=settings.API_V1_PREFIX)
    app.include_router(briefing.router, prefix=settings.API_V1_PREFIX)
    app.include_router(market.router, prefix=settings.API_V1_PREFIX)
    app.include_router(ws_router)  # WebSocket at /ws (no API prefix)

    # Serve frontend (checked last — API routes always win)
    frontend_dir = pathlib.Path(__file__).resolve().parents[4] / "frontend"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")

    return app
