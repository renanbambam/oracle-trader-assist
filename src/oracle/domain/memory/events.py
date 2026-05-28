"""Memory domain — domain events."""

from datetime import datetime

from oracle.domain.shared.base import DomainEvent


class ContextTrimmed(DomainEvent):
    """Fired when context window trimming removes turns to stay under budget.

    The session_id field (from DomainEvent base) identifies which session
    was trimmed. Logged as WARNING — trimming is expected but notable.
    """

    event_type: str = "memory.context_trimmed"
    tokens_removed: int
    turns_removed: int
    remaining_token_count: int


class SessionExpired(DomainEvent):
    """Fired when an idle context session is expired by the system.

    Triggers cleanup of Redis session state and archival in PostgreSQL.
    """

    event_type: str = "memory.session_expired"
    asset: str
    last_active_at: datetime
