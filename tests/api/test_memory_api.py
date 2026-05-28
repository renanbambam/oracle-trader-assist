"""API tests for /api/v1/memory — input validation (no DB required)."""

from httpx import AsyncClient


async def test_get_context_missing_asset_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/memory/context")
    assert response.status_code == 422


async def test_expire_session_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/memory/session/not-a-uuid")
    assert response.status_code == 422


async def test_expire_session_numeric_string_returns_422(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/memory/session/99999")
    assert response.status_code == 422
