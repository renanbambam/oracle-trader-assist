"""EventBroadcaster — bridges the Redis EventBus to connected WebSocket clients.

Lifecycle:
    Started as an asyncio Task in FastAPI's lifespan context.
    Subscribes to ALL Oracle event channels from Redis.
    For each incoming event, routes it to the WebSocketGateway for fan-out.
    Automatically reconnects if the Redis subscription drops.

Design:
    The broadcaster is the only subscriber to the Redis pub/sub channels.
    WebSocket clients subscribe to logical channels via the gateway.
    This separation means Redis pub/sub state is decoupled from WS connections.
"""

import asyncio
from typing import Any

from loguru import logger

from oracle.infrastructure.redis.event_bus import RedisEventBus
from oracle.interface.websocket.gateway import AVAILABLE_CHANNELS, WebSocketGateway

_RECONNECT_DELAY_SECONDS = 3


class EventBroadcaster:
    """Subscribes to all Oracle event channels and broadcasts to WS clients."""

    def __init__(
        self,
        event_bus: RedisEventBus,
        gateway: WebSocketGateway,
    ) -> None:
        self._event_bus = event_bus
        self._gateway = gateway
        self._running = False

    async def run(self) -> None:
        """Run the broadcast loop. Designed to be launched as an asyncio Task."""
        self._running = True
        channels = list(AVAILABLE_CHANNELS)
        logger.info(f"EventBroadcaster started. Channels: {channels}")

        while self._running:
            try:
                async for event in self._event_bus.subscribe(channels):
                    if not self._running:
                        break
                    await self._route(event)

            except asyncio.CancelledError:
                break  # Normal shutdown — stop the loop

            except Exception as exc:
                # Redis dropped the connection or other transient error.
                # Log and reconnect after a delay instead of crashing.
                logger.error(
                    f"EventBroadcaster error: {exc} — "
                    f"reconnecting in {_RECONNECT_DELAY_SECONDS}s"
                )
                await asyncio.sleep(_RECONNECT_DELAY_SECONDS)

        logger.info("EventBroadcaster stopped")

    async def _route(self, event: dict[str, Any]) -> None:
        """Route a single event to the correct WebSocket channel."""
        channel = event.get("channel", "system")
        try:
            await self._gateway.broadcast_to_channel(channel, event)
        except Exception as exc:
            logger.warning(f"EventBroadcaster._route failed for {channel}: {exc}")
