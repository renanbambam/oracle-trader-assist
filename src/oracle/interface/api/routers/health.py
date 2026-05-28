"""Health check endpoints.

Three levels of health check (standard Kubernetes probes):

  GET /api/v1/health        → Basic check (no IO). Always fast.
  GET /api/v1/health/live   → Liveness probe. Returns 200 if process is alive.
  GET /api/v1/health/ready  → Readiness probe. Checks DB + Redis connectivity.
                               Returns 503 if any dependency is unavailable.

All responses include service name, version, environment and timestamp.
"""

from datetime import datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.config.settings import Settings
from oracle.interface.api.dependencies import get_db, get_redis, get_settings

router = APIRouter(prefix="/health", tags=["health"])


def _base_response(settings: Settings, status_value: str) -> dict:
    return {
        "status": status_value,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("", summary="Basic health check")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    """Returns 200 immediately. No IO. Use for basic process liveness."""
    return _base_response(settings, "ok")


@router.get("/live", summary="Liveness probe")
async def liveness(settings: Settings = Depends(get_settings)) -> dict:
    """Kubernetes liveness probe — returns 200 if the process is running."""
    return _base_response(settings, "alive")


@router.get("/ready", summary="Readiness probe")
async def readiness(
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> JSONResponse:
    """Checks connectivity to PostgreSQL and Redis.

    Returns 200 if all dependencies are healthy.
    Returns 503 with details if any dependency is unavailable.
    """
    checks: dict[str, str] = {}
    healthy = True

    # PostgreSQL check
    try:
        await db.execute(text("SELECT 1"))
        checks["postgresql"] = "ok"
    except Exception as exc:
        checks["postgresql"] = f"error: {exc}"
        healthy = False
        logger.warning(f"Health/ready: PostgreSQL check failed: {exc}")

    # Redis check
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False
        logger.warning(f"Health/ready: Redis check failed: {exc}")

    response_body = {
        **_base_response(settings, "ready" if healthy else "degraded"),
        "checks": checks,
    }
    http_status = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=response_body, status_code=http_status)
