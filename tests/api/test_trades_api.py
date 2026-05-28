"""API tests for /api/v1/trades — input validation (no DB required).

422 responses are returned by FastAPI before any IO occurs (Pydantic
validation runs first). These tests are fully deterministic.
"""

from httpx import AsyncClient


async def test_record_trade_missing_body_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/trades", json={})
    assert response.status_code == 422


async def test_record_trade_invalid_direction_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/trades", json={
        "asset": "PETR4",
        "direction": "INVALID_DIR",
        "timeframe": "M5",
        "entry": 28.5,
        "stop": 27.5,
        "target": 30.5,
        "setup": "breakout",
        "emotional_state": "calmo",
    })
    assert response.status_code == 422


async def test_record_trade_invalid_timeframe_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/trades", json={
        "asset": "PETR4",
        "direction": "LONG",
        "timeframe": "INVALID_TF",
        "entry": 28.5,
        "stop": 27.5,
        "target": 30.5,
        "setup": "breakout",
        "emotional_state": "calmo",
    })
    assert response.status_code == 422


async def test_record_trade_negative_entry_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/trades", json={
        "asset": "PETR4",
        "direction": "LONG",
        "timeframe": "M5",
        "entry": -10.0,
        "stop": 27.5,
        "target": 30.5,
        "setup": "breakout",
        "emotional_state": "calmo",
    })
    assert response.status_code == 422


async def test_close_trade_invalid_uuid_path_returns_422(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/trades/not-a-uuid/close",
        json={"trade_id": "not-a-uuid", "exit_price": 29.0, "result": "WIN"},
    )
    assert response.status_code == 422


async def test_close_trade_missing_exit_price_returns_422(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/trades/00000000-0000-0000-0000-000000000001/close",
        json={"trade_id": "00000000-0000-0000-0000-000000000001", "result": "WIN"},
    )
    assert response.status_code == 422
