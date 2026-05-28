"""Common type aliases used across the Oracle domain layer."""

from datetime import datetime, timezone
from typing import TypeAlias
from uuid import UUID, uuid4

# ── Scalar aliases ─────────────────────────────────────────────────────────────
EntityId: TypeAlias = UUID
Timestamp: TypeAlias = datetime
TokenCount: TypeAlias = int
PriceValue: TypeAlias = float
ScoreValue: TypeAlias = float    # 0.0 – 100.0
WeightValue: TypeAlias = float   # 0.0 – 1.0
PercentValue: TypeAlias = float  # 0.0 – 100.0

# ── Factories ──────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    """UTC-aware current timestamp. Prefer this over datetime.utcnow()."""
    return datetime.now(timezone.utc)


def new_uuid() -> UUID:
    """Generate a new UUID v4."""
    return uuid4()
