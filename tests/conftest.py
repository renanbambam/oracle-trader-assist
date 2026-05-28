"""Global test fixtures and configuration.

Test architecture:
    tests/unit/         → Pure Python. No IO. No Docker.
    tests/integration/  → Real PostgreSQL + Redis via testcontainers.
    tests/api/          → FastAPI TestClient with mocked infrastructure.

Fixture scopes:
    session-scoped:  settings, app factory (shared, no IO)
    function-scoped: client (each test gets its own lifespan + HTTP client)

Lifespan note:
    httpx's ASGITransport does not trigger the ASGI lifespan protocol.
    We use asgi-lifespan's LifespanManager in the function-scoped client fixture
    to start/stop the app lifecycle per test. This avoids event loop scope issues
    with session-scoped async fixtures and pytest-asyncio.
"""

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from oracle.config.settings import Settings
from oracle.interface.api.app import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings override for tests — points to test DB/Redis, enables debug."""
    return Settings(
        ENVIRONMENT="test",
        DEBUG=True,
        LOG_LEVEL="WARNING",
        LOG_SERIALIZE=False,
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_USER="oracle",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_DB="oracle_test",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=1,
        ANTHROPIC_API_KEY="test-key-not-used-in-unit-tests",
    )


@pytest.fixture(scope="session")
def app(test_settings: Settings):
    """FastAPI app instance (no lifespan here — managed per-client)."""
    return create_app(settings=test_settings)


@pytest.fixture
async def client(app) -> AsyncClient:
    """Async HTTP test client with lifespan active.

    LifespanManager triggers app startup/shutdown so app.state is populated.
    Redis/DB connections are lazy — no real services needed for API tests.
    Scoped per function so each test gets a clean lifespan cycle.
    """
    async with LifespanManager(app, startup_timeout=10, shutdown_timeout=10) as manager:
        async with AsyncClient(
            transport=ASGITransport(app=manager.app),
            base_url="http://testserver",
        ) as c:
            yield c
