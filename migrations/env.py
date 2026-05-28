import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from oracle.config.settings import get_settings
from oracle.infrastructure.database.base import Base
import oracle.infrastructure.database.models.trade_model  # noqa: F401 — registers model with metadata
import oracle.infrastructure.database.models.analysis_model  # noqa: F401
import oracle.infrastructure.database.models.memory_model  # noqa: F401
import oracle.infrastructure.database.models.analytics_model  # noqa: F401
import oracle.infrastructure.database.models.replay_model  # noqa: F401

config = context.config
fileConfig(config.config_file_name)  # type: ignore[arg-type]

target_metadata = Base.metadata


def _get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_get_url(), echo=False)

    async with engine.connect() as conn:
        await conn.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
            )
        )
        async with conn.begin():
            await conn.run_sync(lambda _: context.run_migrations())

    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
