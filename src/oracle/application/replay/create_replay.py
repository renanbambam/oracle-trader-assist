"""CreateReplayUseCase — builds a new frame-by-frame replay session."""

import random
from datetime import datetime, timedelta

from oracle.application.replay.dtos import CreateReplayInput, ReplayStatusOutput
from oracle.core.ports import EventBus
from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar
from oracle.domain.replay.entities import ReplayFrame, ReplaySession
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState
from oracle.domain.replay.events import ReplayStarted
from oracle.domain.replay.value_objects import TimeRange

_BASE_PRICES: dict[str, float] = {
    "PETR4": 28.50, "VALE3": 68.00, "ITUB4": 30.00,
    "WINFUT": 130_000.0, "DOLFUT": 5_200.0,
}
_MAX_FRAMES = 300


def _timeframe_minutes(tf: Timeframe) -> int:
    mapping = {
        Timeframe.M1: 1, Timeframe.M5: 5, Timeframe.M15: 15,
        Timeframe.M30: 30, Timeframe.H1: 60, Timeframe.H4: 240, Timeframe.D1: 1440,
    }
    return mapping.get(tf, 5)


def _generate_frames(asset: str, timeframe: Timeframe, start: datetime, end: datetime) -> list[ReplayFrame]:
    interval = _timeframe_minutes(timeframe)
    total = int((end - start).total_seconds() / 60 / interval)
    total = min(total, _MAX_FRAMES)

    price = _BASE_PRICES.get(asset.upper(), 100.0)
    frames: list[ReplayFrame] = []
    ts = start

    for i in range(total):
        open_p = round(price, 2)
        close_p = round(open_p * (1 + random.gauss(0, 0.003)), 2)
        high_p = round(max(open_p, close_p) * (1 + abs(random.gauss(0, 0.001))), 2)
        low_p = round(min(open_p, close_p) * (1 - abs(random.gauss(0, 0.001))), 2)
        volume = round(random.uniform(5_000, 100_000), 0)

        bar = OHLCVBar(
            symbol=asset, timeframe=timeframe, timestamp=ts,
            open=open_p, high=high_p, low=low_p, close=close_p, volume=volume,
        )
        frames.append(ReplayFrame(index=i, timestamp=ts, bar=bar))
        price = close_p
        ts += timedelta(minutes=interval)
        if ts > end:
            break

    return frames


class CreateReplayUseCase:
    def __init__(self, repository, event_bus: EventBus) -> None:
        self._repo = repository
        self._event_bus = event_bus

    async def execute(self, data: CreateReplayInput) -> ReplayStatusOutput:
        frames = _generate_frames(data.asset, data.timeframe, data.start, data.end)
        session = ReplaySession(
            asset=data.asset,
            timeframe=data.timeframe,
            range=TimeRange(start=data.start, end=data.end),
            state=ReplayState.IDLE,
            current_frame=0,
            total_frames=len(frames),
            frames=frames,
        )
        await self._repo.save(session)

        await self._event_bus.publish(
            channel="replay",
            event="replay.started",
            payload=ReplayStarted(
                replay_session_id=session.id,
                asset=session.asset,
                timeframe=session.timeframe,
                total_frames=session.total_frames,
                speed=session.speed,
            ).model_dump(mode="json"),
        )

        return replay_to_output(session)


def replay_to_output(session: ReplaySession) -> ReplayStatusOutput:
    return ReplayStatusOutput(
        session_id=session.id,
        asset=session.asset,
        timeframe=session.timeframe,
        state=session.state,
        speed=session.speed,
        current_frame=session.current_frame,
        total_frames=session.total_frames,
        progress_pct=session.progress_pct,
    )
