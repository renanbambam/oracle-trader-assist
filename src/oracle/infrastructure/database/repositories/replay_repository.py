"""PostgreSQL implementation of ReplayRepository."""

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar
from oracle.domain.replay.entities import ReplayFrame, ReplaySession
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState
from oracle.domain.replay.value_objects import FrameAnnotation, TimeRange
from oracle.infrastructure.database.models.replay_model import ReplaySessionOrm


def _to_orm(s: ReplaySession) -> ReplaySessionOrm:
    frames_raw = [f.model_dump(mode="json") for f in s.frames] if s.frames else []
    now = datetime.now(timezone.utc)
    return ReplaySessionOrm(
        id=s.id,
        created_at=s.created_at,
        updated_at=now,
        asset=s.asset,
        timeframe=str(s.timeframe),
        range_start=s.range.start,
        range_end=s.range.end,
        state=str(s.state),
        speed=str(s.speed),
        current_frame=s.current_frame,
        total_frames=s.total_frames,
        frames_json=json.dumps(frames_raw) if frames_raw else None,
    )


def _frames_from_json(raw: str | None) -> list[ReplayFrame]:
    if not raw:
        return []
    frames = []
    for f in json.loads(raw):
        bar_data = f["bar"]
        bar = OHLCVBar(
            symbol=bar_data["symbol"],
            timeframe=Timeframe(bar_data["timeframe"]),
            timestamp=bar_data["timestamp"],
            open=bar_data["open"],
            high=bar_data["high"],
            low=bar_data["low"],
            close=bar_data["close"],
            volume=bar_data["volume"],
            is_complete=bar_data.get("is_complete", True),
        )
        annotations = [FrameAnnotation(**a) for a in f.get("annotations", [])]
        frames.append(
            ReplayFrame(
                index=f["index"],
                timestamp=f["timestamp"],
                bar=bar,
                volume_context=f.get("volume_context", "at_avg"),
                annotations=annotations,
                ai_commentary=f.get("ai_commentary"),
            )
        )
    return frames


def _to_domain(row: ReplaySessionOrm) -> ReplaySession:
    return ReplaySession(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        asset=row.asset,
        timeframe=Timeframe(row.timeframe),
        range=TimeRange(start=row.range_start, end=row.range_end),
        state=ReplayState(row.state),
        speed=PlaybackSpeed(row.speed),
        current_frame=row.current_frame,
        total_frames=row.total_frames,
        frames=_frames_from_json(row.frames_json),
    )


class PostgresReplayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, session: ReplaySession) -> ReplaySession:
        self._session.add(_to_orm(session))
        await self._session.flush()
        return session

    async def get_by_id(self, session_id: UUID) -> ReplaySession | None:
        row = await self._session.get(ReplaySessionOrm, session_id)
        return _to_domain(row) if row else None

    async def update_state(
        self,
        session_id: UUID,
        state: ReplayState,
        current_frame: int,
        speed: PlaybackSpeed,
    ) -> None:
        row = await self._session.get(ReplaySessionOrm, session_id)
        if row:
            row.state = str(state)
            row.current_frame = current_frame
            row.speed = str(speed)
            row.updated_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def save_frame_annotation(
        self,
        session_id: UUID,
        frame_index: int,
        commentary: str,
    ) -> None:
        row = await self._session.get(ReplaySessionOrm, session_id)
        if not row:
            raise ValueError(f"Replay session {session_id} not found")
        frames = _frames_from_json(row.frames_json)
        if frame_index >= len(frames):
            raise ValueError(f"Frame {frame_index} out of range")
        frames[frame_index] = frames[frame_index].model_copy(update={"ai_commentary": commentary})
        row.frames_json = json.dumps([f.model_dump(mode="json") for f in frames])
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def get_by_asset(self, asset: str, limit: int = 10) -> list[ReplaySession]:
        stmt = (
            select(ReplaySessionOrm)
            .where(ReplaySessionOrm.asset == asset)
            .order_by(ReplaySessionOrm.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
