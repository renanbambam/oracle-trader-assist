"""Replay domain — domain events."""

from datetime import datetime
from uuid import UUID

from oracle.domain.market.enums import Timeframe
from oracle.domain.market.value_objects import OHLCVBar
from oracle.domain.replay.enums import PlaybackSpeed
from oracle.domain.shared.base import DomainEvent


class ReplayStarted(DomainEvent):
    """Fired when a replay session begins playback."""

    event_type: str = "replay.started"
    replay_session_id: UUID
    asset: str
    timeframe: Timeframe
    total_frames: int
    speed: PlaybackSpeed


class ReplayPaused(DomainEvent):
    """Fired when replay is paused at a specific frame."""

    event_type: str = "replay.paused"
    replay_session_id: UUID
    current_frame: int
    current_timestamp: datetime


class ReplayFrameAdvanced(DomainEvent):
    """Fired on each frame advance — primary driver of real-time UI updates.

    Carries the full OHLCVBar so clients can render the candle without
    a follow-up REST call.
    """

    event_type: str = "replay.frame_advanced"
    replay_session_id: UUID
    frame_index: int
    timestamp: datetime
    bar: OHLCVBar


class ReplayCompleted(DomainEvent):
    """Fired when replay reaches the final frame."""

    event_type: str = "replay.completed"
    replay_session_id: UUID
    total_frames_visited: int
