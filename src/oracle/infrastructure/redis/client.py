"""Redis async client factory.

Uses redis-py's built-in asyncio support with hiredis for performance.
A single client instance is created at startup and shared across requests.

Usage (via FastAPI DI):
    redis = app.state.redis
    await redis.set("key", "value", ex=60)
"""

import redis.asyncio as aioredis

from oracle.config.settings import Settings


def build_redis_client(settings: Settings) -> aioredis.Redis:
    """Create a Redis client from application settings.

    Returns a connection pool backed client — not a single connection.
    Thread-safe and coroutine-safe by default.
    """
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,  # Strings, not bytes
        max_connections=50,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
    )
