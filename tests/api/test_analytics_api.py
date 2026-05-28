"""API tests for /api/v1/analytics — input validation (no DB required)."""

from httpx import AsyncClient


async def test_performance_invalid_period_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/performance?period=INVALID")
    assert response.status_code == 422


async def test_performance_invalid_period_value_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analytics/performance?period=yearly")
    assert response.status_code == 422
