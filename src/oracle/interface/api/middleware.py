"""FastAPI middleware stack.

Middleware executes in reverse registration order (outermost = last registered).
Registration order in app.py:
    1. CORSMiddleware        ← FastAPI's built-in, registered via add_middleware
    2. CorrelationIdMiddleware
    3. RequestLoggingMiddleware

CorrelationIdMiddleware:
    Reads X-Correlation-ID from the request header (or generates a UUID4).
    Sets it on the contextvars.ContextVar so it propagates to every log line
    and downstream call within this request's async context.

RequestLoggingMiddleware:
    Logs method, path, status code and response time for every HTTP request.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from oracle.core.logging import correlation_id_var


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject a correlation ID into every request's async context.

    The ID is sourced from the incoming X-Correlation-ID header if present,
    otherwise a new UUID4 is generated. The same ID is echoed back on the
    response header so callers can correlate their logs with server logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Store in ContextVar — propagates through the entire async call chain
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)  # Clean up after request completes

        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status and duration."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} "
            f"({duration_ms:.1f}ms)"
        )
        return response
