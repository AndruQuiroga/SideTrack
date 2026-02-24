"""Declarative base for the rebooted Sidetrack API models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all new SQLAlchemy models in the API service."""

    pass
