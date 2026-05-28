"""Memory application — input/output DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from oracle.domain.memory.enums import MessageRole, SessionStatus


class LoadContextInput(BaseModel):
    asset: str
    create_if_missing: bool = True


class ContextOutput(BaseModel):
    session_id: UUID
    asset: str
    status: SessionStatus
    token_count: int
    turn_count: int
    usage_pct: float
    last_active_at: datetime


class AppendMessageInput(BaseModel):
    session_id: UUID
    role: MessageRole
    content: str


class SearchHistoryInput(BaseModel):
    asset: str
    setup_type: str
    limit: int = Field(default=5, ge=1, le=20)


class SearchHistoryRecord(BaseModel):
    id: UUID
    asset: str
    setup_type: str
    content: str
    relevance_score: float | None
    created_at: datetime


class SearchHistoryOutput(BaseModel):
    records: list[SearchHistoryRecord]
    prompt_context: str
