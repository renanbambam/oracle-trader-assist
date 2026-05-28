"""Memory domain — entities."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from oracle.domain.memory.enums import MessageRole, SessionStatus, TrimStrategy
from oracle.domain.memory.value_objects import ContextWindow, TokenBudget
from oracle.domain.shared.base import Entity


class ChatMessage(Entity):
    """A single turn in a conversation with the AI."""

    session_id: UUID
    role: MessageRole
    content: str
    token_count: int | None = None
    analysis_id: UUID | None = None


class MemoryRecord(Entity):
    """Persisted knowledge extracted from past trades and analyses.

    Provides historical context during future analyses. Foundation for
    future RAG/embedding search (embedding_id will reference a vector store).
    """

    asset: str
    setup_type: str
    content: str
    source_analysis_id: UUID | None = None
    source_trade_id: UUID | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    embedding_id: str | None = None


class ContextSession(Entity):
    """Active multi-turn conversation context for a specific asset.

    Manages token budget and turn history. One active session per asset
    at a time. Transitions to EXPIRED after inactivity or manual close.
    """

    asset: str
    status: SessionStatus = SessionStatus.ACTIVE
    token_count: int = Field(default=0, ge=0)
    turns: list[ChatMessage] = Field(default_factory=list)
    context_window: ContextWindow | None = None
    token_budget: TokenBudget = Field(default_factory=TokenBudget)
    trim_strategy: TrimStrategy = TrimStrategy.OLDEST_FIRST
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    last_active_at: datetime

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE


class SessionState(Entity):
    """Lightweight snapshot of active session metadata stored in Redis.

    Avoids loading the full ContextSession (which includes all turns)
    for quick status checks and metadata lookups.
    """

    asset: str
    status: SessionStatus = SessionStatus.ACTIVE
    token_count: int = Field(default=0, ge=0)
    turn_count: int = Field(default=0, ge=0)
    last_analysis_id: UUID | None = None
    last_trade_id: UUID | None = None
    last_active_at: datetime
