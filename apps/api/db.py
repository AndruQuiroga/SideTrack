"""Database engine and session management for the API service."""

from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal: Optional[sessionmaker] = None


def init_engine(database_url: str) -> None:
    """Initialize a singleton engine and session factory.

    Calling this function multiple times is safe; only the first call will
    create the engine and sessionmaker.
    """

    global _engine, _SessionLocal

    if _engine is None:
        _engine = create_engine(database_url, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped use."""

    if _SessionLocal is None:
        raise RuntimeError("Database engine is not initialized. Call init_engine() first.")

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
