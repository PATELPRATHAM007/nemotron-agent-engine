"""
SQLAlchemy Declarative Base
===========================
Defines the base class for all persistent database models.
Decoupled from database session creation to eliminate circular dependencies.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass
