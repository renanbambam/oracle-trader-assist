"""API tests for /api/v1/replay — input validation (no DB required).

The end-before-start test is deterministic (422): TimeRange.model_validator
raises ValueError before repo.save() is ever called.
"""

from httpx import AsyncClient


async def test_create_replay_missing_body_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/replay", json={})
    assert response.status_code == 422


async def test_create_replay_invalid_timeframe_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/replay", json={
        "asset": "PETR4",
        "timeframe": "INVALID",
        "start": "2024-06-01T09:00:00Z",
        "end": "2024-06-01T17:30:00Z",
    })
    assert response.status_code == 422


async def test_create_replay_missing_start_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/replay", json={
        "asset": "PETR4",
        "timeframe": "M5",
        "end": "2024-06-01T17:30:00Z",
    })
    assert response.status_code == 422


async def test_create_replay_end_before_start_returns_422(client: AsyncClient) -> None:
    # TimeRange model_validator raises ValueError → router catches → 422
    # This is deterministic: frame generation and TimeRange creation happen
    # before any repo call.
    response = await client.post("/api/v1/replay", json={
        "asset": "PETR4",
        "timeframe": "M5",
        "start": "2024-06-01T17:00:00Z",
        "end": "2024-06-01T09:00:00Z",
    })
    assert response.status_code == 422


async def test_next_frame_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.put("/api/v1/replay/not-a-uuid/next")
    assert response.status_code == 422


async def test_finish_invalid_uuid_returns_422(client: AsyncClient) -> None:
    response = await client.put("/api/v1/replay/not-a-uuid/finish")
    assert response.status_code == 422
