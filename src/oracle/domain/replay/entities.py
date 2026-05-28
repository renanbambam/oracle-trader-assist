"""Replay domain — entities."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState
from oracle.domain.replay.value_objects import FrameAnnotation, TimeRange
from oracle.domain.shared.base import Entity, ValueObject


class ReplayFrame(ValueObject):
    """Single immutable frame in a replay timeline.

    A frame is the atomic unit of replay — one OHLCV bar at a point in time.
    AI commentary is generated on demand when the trader requests annotation;
    it is not pre-computed for all frames.
    """

    index: int = Field(ge=0)
    timestamp: datetime
    bar: OHLCVBar
    volume_context: str = "at_avg"
    annotations: list[FrameAnnotation] = Field(default_factory=list)
    ai_commentary: str | None = None

    @property
    def has_ai_commentary(self) -> bool:
        return self.ai_commentary is not None

    @property
    def has_annotations(self) -> bool:
        return len(self.annotations) > 0


class ReplayTimeline(ValueObject):
    """Lightweight snapshot of a replay session's navigation state.

    Sent to WebSocket clients on every frame advance.
    Does not include the full frames list (too large for streaming).
    """

    session_id: UUID
    asset: str
    timeframe: Timeframe
    total_frames: int
    current_index: int
    state: ReplayState
    speed: PlaybackSpeed


class ReplaySession(Entity):
    """A replay session for a specific asset/timeframe/timerange.

    Allows traders to revisit historical data frame-by-frame for training
    and post-mortem analysis. State transitions managed by ReplayEngine
    (domain service).
    """

    asset: str
    timeframe: Timeframe
    range: TimeRange
    state: ReplayState = ReplayState.IDLE
    speed: PlaybackSpeed = PlaybackSpeed.X1
    current_frame: int = Field(default=0, ge=0)
    total_frames: int = Field(default=0, ge=0)
    frames: list[ReplayFrame] = Field(default_factory=list)

    @property
    def current_frame_data(self) -> ReplayFrame | None:
        if not self.frames or self.current_frame >= len(self.frames):
            return None
        return self.frames[self.current_frame]

    @property
    def is_at_end(self) -> bool:
        return self.current_frame >= self.total_frames - 1

    @property
    def progress_pct(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return round(self.current_frame / self.total_frames * 100, 1)

    @property
    def timeline_snapshot(self) -> ReplayTimeline:
        """Lightweight snapshot suitable for WebSocket broadcast."""
        return ReplayTimeline(
            session_id=self.id,
            asset=self.asset,
            timeframe=self.timeframe,
            total_frames=self.total_frames,
            current_index=self.current_frame,
            state=self.state,
            speed=self.speed,
        )
