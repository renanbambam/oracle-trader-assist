"""Redis-backed EventBus — implements the EventBus port via Redis pub/sub.

Architecture:
  Domain/Application  →  EventBus (port in core/ports.py)
  Infrastructure      →  RedisEventBus (this file)

Channel naming convention:
  All channels are prefixed with "oracle:events:" in Redis.
  Logical names passed to publish/subscribe are the short form.
  Example: channel="analysis" → Redis key "oracle:events:analysis"

Usage:
    event_bus = RedisEventBus(redis_client)

    # Publish
    await event_bus.publish(
        channel="analysis",
        event="analysis.completed",
        payload={"asset": "PETR4", "confidence_score": 78},
    )

    # Subscribe (async generator)
    async for event in event_bus.subscribe(["analysis", "trading"]):
        print(event)  # {"event": "...", "channel": "...", "payload": {...}}
"""

import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import redis.asyncio as aioredis
from loguru import logger

_CHANNEL_PREFIX = "oracle:events"


class RedisEventBus:
    """EventBus implementation using Redis pub/sub.

    Satisfies the EventBus Protocol defined in core/ports.py.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def publish(
        self,
        channel: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to a Redis channel.

        Non-blocking. If no subscribers are listening, the event is dropped
        (standard pub/sub semantics — not a message queue).
        """
        message = {
            "event": event,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        redis_channel = f"{_CHANNEL_PREFIX}:{channel}"
        await self._redis.publish(redis_channel, json.dumps(message))
        logger.debug(f"EventBus.publish: {event} → {channel}")

    async def subscribe(
        self,
        channels: list[str],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to channels and yield incoming events.

        This is an infinite async generator. The caller controls the lifecycle:
        - Use in an async for loop (will run until cancelled).
        - Cancel the enclosing Task to stop.

        Cleans up the pubsub subscription on exit (even on error).
        """
        pubsub = self._redis.pubsub()
        redis_channels = [f"{_CHANNEL_PREFIX}:{ch}" for ch in channels]

        try:
            await pubsub.subscribe(*redis_channels)
            logger.info(f"EventBus.subscribe: listening on {channels}")

            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    # Ignore subscription confirmations and other control msgs
                    continue
                try:
                    yield json.loads(raw["data"])
                except (json.JSONDecodeError, KeyError) as exc:
                    logger.warning(f"EventBus: malformed message skipped: {exc}")

        finally:
            await pubsub.unsubscribe(*redis_channels)
            await pubsub.aclose()
            logger.info(f"EventBus.subscribe: unsubscribed from {channels}")
