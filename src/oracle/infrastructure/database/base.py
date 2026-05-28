"""SQLAlchemy declarative base for all ORM models.

All ORM model classes inherit from Base. This file must have no circular
imports — it is imported by both connection.py and migrations/env.py.

Usage:
    from oracle.infrastructure.database.base import Base

    class TradeOrm(Base):
        __tablename__ = "trades"
        ...
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all Oracle ORM models.

    Import oracle domain-specific ORM models in migrations/env.py so that
    Alembic autogenerate can detect schema changes.
    """
