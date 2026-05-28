"""Tests for the health check endpoints.

These tests use the FastAPI test client and do NOT require a running DB or Redis.
The /health and /health/live endpoints are pure (no IO).
The /health/ready endpoint is expected to return 503 in the test environment
because no real PostgreSQL/Redis is available.
"""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Oracle Trader Assist"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


async def test_health_includes_environment(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["environment"] == "test"


async def test_liveness_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


async def test_readiness_returns_valid_structure(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    # May be 200 (if services available) or 503 (if not) — both are valid
    assert response.status_code in (200, 503)

    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "postgresql" in data["checks"]
    assert "redis" in data["checks"]


async def test_correlation_id_header_echoed(client: AsyncClient) -> None:
    correlation_id = "test-correlation-abc-123"
    response = await client.get(
        "/api/v1/health",
        headers={"X-Correlation-ID": correlation_id},
    )

    assert response.headers.get("x-correlation-id") == correlation_id


async def test_new_correlation_id_generated_if_absent(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    # Server should have generated and echoed back a UUID
    correlation_id = response.headers.get("x-correlation-id")
    assert correlation_id is not None
    assert len(correlation_id) == 36  # UUID4 format
