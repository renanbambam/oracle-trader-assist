"""Structured logging setup using Loguru.

Correlation IDs are stored in a ContextVar so they propagate through the
entire async call chain without explicit passing.

Usage:
    from oracle.core.logging import setup_logging, correlation_id_var
    setup_logging(level="INFO")
"""

import contextvars
import logging
import sys

from loguru import logger


class _InterceptHandler(logging.Handler):
    """Forward stdlib logging records to loguru (captures uvicorn/APScheduler errors)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Thread/async-safe storage for per-request correlation ID.
# Set by CorrelationIdMiddleware; read by the log patcher below.
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="-",
)

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[correlation_id]:<36}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def _inject_correlation_id(record: dict) -> None:
    """Loguru patcher — adds current correlation_id to every log record."""
    record["extra"]["correlation_id"] = correlation_id_var.get("-")


def setup_logging(level: str = "INFO", serialize: bool = False) -> None:
    """Configure Loguru for the application.

    Args:
        level:     Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        serialize: If True, emit JSON (for production log aggregation).
                   If False, emit coloured human-readable output.
    """
    logger.remove()  # Remove Loguru's default handler

    logger.configure(patcher=_inject_correlation_id)

    if serialize:
        logger.add(sys.stdout, level=level, serialize=True, enqueue=True)
    else:
        logger.add(
            sys.stderr,
            level=level,
            format=_CONSOLE_FORMAT,
            colorize=True,
            enqueue=True,  # thread-safe async logging
        )

    # Intercept stdlib logging so uvicorn/APScheduler errors appear in loguru output.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
