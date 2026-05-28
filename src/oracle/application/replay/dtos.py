"""Replay application — input/output DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from oracle.domain.market.enums import Timeframe
from oracle.domain.replay.enums import PlaybackSpeed, ReplayState


class CreateReplayInput(BaseModel):
    asset: str
    timeframe: Timeframe
    start: datetime
    end: datetime


class ControlReplayInput(BaseModel):
    """Unified control DTO for all replay actions.

    - play / pause / step / step_back: no extra fields needed
    - seek: requires frame_index
    - set_speed: requires speed
    """

    action: str = Field(pattern="^(play|pause|step|step_back|seek|set_speed)$")
    frame_index: int | None = Field(default=None, ge=0)
    speed: PlaybackSpeed | None = None


class ReplayStatusOutput(BaseModel):
    session_id: UUID
    asset: str
    timeframe: Timeframe
    state: ReplayState
    speed: PlaybackSpeed
    current_frame: int
    total_frames: int
    progress_pct: float


class AnnotateFrameInput(BaseModel):
    frame_index: int = Field(ge=0)


class AnnotateFrameOutput(BaseModel):
    session_id: UUID
    frame_index: int
    commentary: str
