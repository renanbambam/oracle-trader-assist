"""SQLAlchemy async engine and session factory.

Design decisions:
- pool_pre_ping=True: validates connections before use (handles DB restarts)
- expire_on_commit=False: avoids lazy-loading errors in async context
- autoflush=False: explicit control over when SQL is sent

Usage (via FastAPI DI):
    async with get_session() as session:
        result = await session.execute(select(TradeOrm))
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from oracle.config.settings import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Create the SQLAlchemy async engine from application settings."""
    return create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,        # Logs SQL in DEBUG mode
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,         # Re-validate stale connections
        pool_recycle=3600,          # Recycle connections every hour
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,     # Safe for async — avoids implicit IO
        autocommit=False,
        autoflush=False,
    )
