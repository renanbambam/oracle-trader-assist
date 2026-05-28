"""WebSocket cold start — provides channel state snapshots for reconnecting clients.

Called once per subscribe action so the client immediately sees current system state
without waiting for the next event. Designed to be non-fatal: errors are caught and
logged so a failing snapshot never blocks WS connection establishment.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


def make_snapshot_provider(
    engine: AsyncEngine,
) -> Callable[[str], Awaitable[dict[str, Any] | None]]:
    """Return an async callable that fetches the current snapshot for a channel."""

    async def provider(channel: str) -> dict[str, Any] | None:
        try:
            return await _fetch(channel, engine)
        except Exception as exc:
            logger.warning(f"Cold start snapshot failed [{channel}]: {exc}")
            return None

    return provider


async def _fetch(channel: str, engine: AsyncEngine) -> dict[str, Any] | None:
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    if channel == "trading":
        async with factory() as session:
            from oracle.domain.trade.enums import TradeStatus
            from oracle.infrastructure.database.repositories.trade_repository import (
                PostgresTradeRepository,
            )

            repo = PostgresTradeRepository(session)
            open_trades = await repo.get_by_status(TradeStatus.OPEN)
            recent = await repo.get_recent(limit=5)
            return {
                "event": "trading.snapshot",
                "channel": "trading",
                "payload": {
                    "open_count": len(open_trades),
                    "recent_trades": [
                        {
                            "id": str(t.id),
                            "asset": t.asset,
                            "direction": str(t.direction),
                            "status": str(t.status),
                            "entry": t.entry,
                            "result": str(t.result) if t.result else None,
                        }
                        for t in recent
                    ],
                },
            }

    if channel == "analysis":
        async with factory() as session:
            from oracle.infrastructure.database.models.analysis_model import ChartAnalysisOrm
            from sqlalchemy import select

            stmt = (
                select(ChartAnalysisOrm)
                .where(ChartAnalysisOrm.status == "completed")
                .order_by(ChartAnalysisOrm.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalars().first()
            if row is None:
                return None
            return {
                "event": "analysis.snapshot",
                "channel": "analysis",
                "payload": {
                    "analysis_id": str(row.id),
                    "asset": row.asset,
                    "timeframe": row.timeframe,
                    "suggestion": row.suggestion,
                    "confidence_score": row.confidence_score,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                },
            }

    if channel == "replay":
        async with factory() as session:
            from oracle.infrastructure.database.models.replay_model import ReplaySessionOrm
            from sqlalchemy import select

            stmt = (
                select(ReplaySessionOrm)
                .where(ReplaySessionOrm.state.in_(["idle", "playing", "paused"]))
                .order_by(ReplaySessionOrm.created_at.desc())
                .limit(3)
            )
            rows = (await session.execute(stmt)).scalars().all()
            if not rows:
                return None
            return {
                "event": "replay.snapshot",
                "channel": "replay",
                "payload": {
                    "active_sessions": [
                        {
                            "session_id": str(r.id),
                            "asset": r.asset,
                            "timeframe": r.timeframe,
                            "state": r.state,
                            "current_frame": r.current_frame,
                            "total_frames": r.total_frames,
                        }
                        for r in rows
                    ],
                },
            }

    return None
