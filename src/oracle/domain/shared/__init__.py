"""Shared base abstractions — the foundation of the Oracle domain layer."""

from oracle.domain.shared.base import DomainEvent, Entity, ValueObject
from oracle.domain.shared.types import (
    EntityId,
    PercentValue,
    PriceValue,
    ScoreValue,
    Timestamp,
    TokenCount,
    WeightValue,
    new_uuid,
    utcnow,
)

__all__ = [
    "Entity",
    "ValueObject",
    "DomainEvent",
    "EntityId",
    "Timestamp",
    "TokenCount",
    "PriceValue",
    "ScoreValue",
    "WeightValue",
    "PercentValue",
    "utcnow",
    "new_uuid",
]
