"""API tests for /api/v1/analyses — input validation (no DB required)."""

from httpx import AsyncClient


async def test_run_analysis_missing_body_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analyses", json={})
    assert response.status_code == 422


async def test_run_analysis_missing_asset_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analyses", json={"timeframe": "M5"})
    assert response.status_code == 422


async def test_run_analysis_missing_timeframe_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analyses", json={"asset": "PETR4"})
    assert response.status_code == 422


async def test_run_analysis_invalid_timeframe_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/analyses", json={
        "asset": "PETR4",
        "timeframe": "INVALID_TF",
    })
    assert response.status_code == 422


async def test_get_analysis_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analyses/not-a-uuid")
    assert response.status_code == 422


async def test_get_analysis_wrong_type_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.get("/api/v1/analyses/12345")
    assert response.status_code == 422
