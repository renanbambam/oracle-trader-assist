"""Memory domain — enumerations."""

from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class TrimStrategy(StrEnum):
    """Strategy used when context exceeds the token budget.

    OLDEST_FIRST is the default and simplest — removes oldest turns first.
    SUMMARIZE will be supported in Phase 2 via a dedicated summarization call.
    """
    OLDEST_FIRST = "oldest_first"
    SUMMARIZE = "summarize"
    SELECTIVE = "selective"
