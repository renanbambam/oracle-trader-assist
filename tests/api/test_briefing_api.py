"""API tests for /api/v1/briefing — route registration via OpenAPI spec.

The morning briefing endpoint always needs DB + Claude AI, so we can't
test it end-to-end without those services. Instead we verify the route is
registered by inspecting the OpenAPI spec (no IO required).
"""

from httpx import AsyncClient


async def test_morning_briefing_route_in_openapi(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/briefing/morning" in paths


async def test_morning_briefing_is_get_method(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    paths = response.json()["paths"]
    assert "get" in paths["/api/v1/briefing/morning"]
