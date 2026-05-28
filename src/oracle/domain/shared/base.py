"""Base abstractions for all domain entities, value objects and events."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ValueObject(BaseModel):
    """Immutable — equality by value, no identity.

    All value objects must be frozen. Use to represent concepts that
    are fully described by their attributes (price, score, range, etc).
    """

    model_config = ConfigDict(frozen=True)


class Entity(BaseModel):
    """Has identity — equality by id, mutable lifecycle.

    Entities are persisted, have a UUID primary key, and carry timestamps.
    Subclasses should not override id/created_at/updated_at unless justified.
    """

    model_config = ConfigDict(frozen=False, use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class DomainEvent(BaseModel):
    """Immutable fact — something relevant happened in the domain.

    Events are emitted by the application layer after state changes.
    Consumed by the EventBus to fan-out to WebSocket clients and other
    bounded contexts. Always frozen; never mutated after creation.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=_utcnow)
    correlation_id: str | None = None
    session_id: UUID | None = None
