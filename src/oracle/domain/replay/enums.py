"""Replay domain — enumerations."""

from enum import StrEnum


class ReplayState(StrEnum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"


class PlaybackSpeed(StrEnum):
    X1 = "1x"
    X2 = "2x"
    X5 = "5x"
    X10 = "10x"
