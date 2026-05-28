"""OracleScheduler — APScheduler wrapper with Redis jobstore.

Thin orchestration layer that knows nothing about specific jobs.
Jobs are registered externally (in app lifespan) via add_cron_job()
and add_interval_job().
"""

from collections.abc import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger


def _build_jobstores() -> dict:
    # MemoryJobStore: jobs carry non-picklable kwargs (SQLAlchemy engine).
    # Redis jobstore would pickle kwargs on every add_job call and fail.
    # Jobs are re-registered from the app lifespan on every startup, so
    # in-memory storage is sufficient and avoids the pickle limitation.
    from apscheduler.jobstores.memory import MemoryJobStore
    return {"default": MemoryJobStore()}


class OracleScheduler:
    """Lifecycle-aware APScheduler wrapper.

    Usage:
        scheduler = OracleScheduler(redis_url, timezone)
        scheduler.add_cron_job(my_func, hour=7, minute=0, kwargs={...})
        scheduler.start()
        # ... app runs ...
        scheduler.shutdown()
    """

    def __init__(self, redis_url: str = "", timezone: str = "America/Sao_Paulo") -> None:
        jobstores = _build_jobstores()
        executors = {"default": {"type": "asyncio"}}
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone=timezone,
        )

    def add_cron_job(
        self,
        func: Callable,
        *,
        job_id: str,
        day_of_week: str = "mon-fri",
        hour: int,
        minute: int = 0,
        kwargs: dict | None = None,
    ) -> None:
        self._scheduler.add_job(
            func,
            "cron",
            id=job_id,
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            kwargs=kwargs or {},
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f"Scheduler: registered cron job '{job_id}' at {hour:02d}:{minute:02d} [{day_of_week}]")

    def add_interval_job(
        self,
        func: Callable,
        *,
        job_id: str,
        minutes: int,
        kwargs: dict | None = None,
    ) -> None:
        self._scheduler.add_job(
            func,
            "interval",
            id=job_id,
            minutes=minutes,
            kwargs=kwargs or {},
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(f"Scheduler: registered interval job '{job_id}' every {minutes}min")

    def start(self) -> None:
        self._scheduler.start()
        logger.info("OracleScheduler started")

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("OracleScheduler stopped")
