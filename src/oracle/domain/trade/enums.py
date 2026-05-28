"""Trade domain — enumerations."""

from enum import StrEnum


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TradeResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


class EmotionalState(StrEnum):
    """Trader's emotional state at the time of entry.

    FOMO and REVANCHE are the two states most correlated with bad outcomes
    — they trigger the AntiFOMOFilter warning in the checklist.
    """
    CALMO = "calmo"
    ANSIOSO = "ansioso"
    FOMO = "fomo"
    REVANCHE = "revanche"
    CONFIANTE = "confiante"
    HESITANTE = "hesitante"
    NEUTRO = "neutro"
