"""WebSocket connection manager and endpoint.

Architecture:
    Clients connect to ws://host/ws
    Each connection gets a UUID client_id
    Clients subscribe to channels by sending:
        {"action": "subscribe", "channels": ["market", "analysis"]}
    Server pushes events as they arrive from the EventBus (via broadcaster.py)
    Heartbeat: server sends ping every WS_HEARTBEAT_INTERVAL seconds

Message formats:

  Inbound (client → server):
    {"action": "subscribe", "channels": ["market", "analysis", "trading"]}
    {"action": "unsubscribe", "channels": ["market"]}
    {"action": "pong"}

  Outbound (server → client):
    {"event": "analysis.completed", "channel": "analysis", "payload": {...}}
    {"event": "system.ping", "channel": "system", "payload": {}}
    {"event": "system.connected", "channel": "system",
     "payload": {"client_id": "...", "available_channels": [...]}}
"""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from oracle.config.settings import get_settings

# All channels the gateway can route events to
AVAILABLE_CHANNELS = frozenset(
    ["market", "analysis", "ai_stream", "trading", "replay", "system"]
)

router = APIRouter(tags=["websocket"])


class WebSocketGateway:
    """Manages WebSocket connections, subscriptions and message routing."""

    def __init__(self, max_connections: int = 100, snapshot_provider=None) -> None:
        self._max_connections = max_connections
        # client_id → WebSocket connection
        self._connections: dict[str, WebSocket] = {}
        # client_id → set of subscribed channels
        self._subscriptions: dict[str, set[str]] = {}
        # Optional async callable(channel) → snapshot dict | None
        self._snapshot_provider = snapshot_provider

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, client_id: str, websocket: WebSocket) -> bool:
        """Accept and register a new WebSocket connection.

        Returns False if the connection limit has been reached.
        """
        if len(self._connections) >= self._max_connections:
            await websocket.close(code=1013, reason="Connection limit reached")
            logger.warning(f"WS connection rejected (limit={self._max_connections})")
            return False

        await websocket.accept()
        self._connections[client_id] = websocket
        self._subscriptions[client_id] = set()

        # Notify client of successful connection
        await self._send(
            client_id,
            {
                "event": "system.connected",
                "channel": "system",
                "payload": {
                    "client_id": client_id,
                    "available_channels": sorted(AVAILABLE_CHANNELS),
                },
            },
        )
        logger.info(
            f"WS connected: {client_id} "
            f"(total={len(self._connections)})"
        )
        return True

    async def disconnect(self, client_id: str) -> None:
        """Deregister a client and clean up its subscriptions."""
        self._connections.pop(client_id, None)
        self._subscriptions.pop(client_id, None)
        logger.info(
            f"WS disconnected: {client_id} "
            f"(total={len(self._connections)})"
        )

    async def handle_message(self, client_id: str, data: dict[str, Any]) -> None:
        """Process an inbound message from a connected client."""
        action = data.get("action")

        if action == "subscribe":
            channels = set(data.get("channels", [])) & AVAILABLE_CHANNELS
            new_channels = channels - self._subscriptions.get(client_id, set())
            self._subscriptions[client_id].update(channels)
            logger.debug(f"WS {client_id} subscribed to: {channels}")

            if new_channels and self._snapshot_provider:
                for ch in sorted(new_channels):
                    try:
                        snapshot = await self._snapshot_provider(ch)
                        if snapshot:
                            await self._send(client_id, snapshot)
                    except Exception as exc:
                        logger.warning(f"Cold start [{ch}] failed: {exc}")

        elif action == "unsubscribe":
            channels = set(data.get("channels", []))
            self._subscriptions[client_id].discard(*channels) if channels else None
            logger.debug(f"WS {client_id} unsubscribed from: {channels}")

        elif action == "pong":
            pass  # Heartbeat acknowledged

        else:
            logger.debug(f"WS {client_id}: unknown action '{action}' — ignored")

    async def broadcast_to_channel(
        self,
        channel: str,
        message: dict[str, Any],
    ) -> None:
        """Send a message to all clients subscribed to the given channel."""
        if not self._connections:
            return

        targets = [
            client_id
            for client_id, channels in self._subscriptions.items()
            if channel in channels
        ]
        if not targets:
            return

        # Fan-out concurrently — one slow client doesn't block others
        await asyncio.gather(
            *[self._send(client_id, message) for client_id in targets],
            return_exceptions=True,  # Don't abort on individual send failures
        )

    async def ping_all(self) -> None:
        """Send a ping to all connected clients (heartbeat)."""
        message = {"event": "system.ping", "channel": "system", "payload": {}}
        await asyncio.gather(
            *[self._send(cid, message) for cid in list(self._connections)],
            return_exceptions=True,
        )

    async def _send(self, client_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to a specific client, disconnecting on error."""
        websocket = self._connections.get(client_id)
        if not websocket:
            return
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.warning(f"WS send failed for {client_id}: {exc} — disconnecting")
            await self.disconnect(client_id)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket connection endpoint.

    Clients connect here and receive real-time events from the Oracle system.
    """
    settings = get_settings()
    gateway: WebSocketGateway = websocket.app.state.ws_gateway
    client_id = str(uuid.uuid4())

    connected = await gateway.connect(client_id, websocket)
    if not connected:
        return

    # Start heartbeat task for this connection
    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            if client_id not in gateway._connections:
                break
            await gateway._send(
                client_id,
                {"event": "system.ping", "channel": "system", "payload": {}},
            )

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            data = await websocket.receive_json()
            await gateway.handle_message(client_id, data)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(f"WS error for {client_id}: {exc}")
    finally:
        heartbeat_task.cancel()
        await gateway.disconnect(client_id)
