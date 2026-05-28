"""Integration test fixtures — real PostgreSQL via docker-compose.test.yml or testcontainers.

Priority:
  1. Use postgres-test / redis-test containers from docker-compose.test.yml (localhost:5433/6380).
  2. Fall back to testcontainers if those ports are not open.

Tests in this suite are skipped when neither Docker nor the compose containers are available.
"""

import socket

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import oracle.infrastructure.database.models.analysis_model  # noqa: F401
import oracle.infrastructure.database.models.analytics_model  # noqa: F401
import oracle.infrastructure.database.models.replay_model  # noqa: F401
import oracle.infrastructure.database.models.memory_model  # noqa: F401
import oracle.infrastructure.database.models.trade_model  # noqa: F401
from oracle.infrastructure.database.base import Base


# ── Environment detection ─────────────────────────────────────────────────────

_COMPOSE_PG_URL = (
    "postgresql+asyncpg://oracle_test:oracle_test@localhost:5433/oracle_test"
)


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def _docker_available() -> bool:
    try:
        import docker
        docker.from_env().ping()
        return True
    except Exception:
        return False


_USE_COMPOSE = _is_port_open("localhost", 5433)
_HAS_DOCKER   = _docker_available()

requires_docker = pytest.mark.skipif(
    not (_USE_COMPOSE or _HAS_DOCKER),
    reason="Docker not available — skipping integration tests",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def postgres_container():
    """Yield a testcontainers PostgresContainer, or None when using compose."""
    if _USE_COMPOSE:
        yield None
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(postgres_container) -> str:
    if postgres_container is None:
        return _COMPOSE_PG_URL
    url = postgres_container.get_connection_url()
    return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
async def engine(db_url: str):
    eng = create_async_engine(db_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
        await s.rollback()
