"""Database engine and session management for the API service."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
_SessionLocal: sessionmaker | None = None


def init_engine(database_url: str) -> None:
    """Initialize a singleton engine and session factory.

    Calling this function multiple times is safe; only the first call will
    create the engine and sessionmaker.
    """

    global _engine, _SessionLocal

    if _engine is None:
        # Bound connection attempts so a hung database can't stall workers indefinitely.
        connect_args = {"connect_timeout": 5} if database_url.startswith("postgresql") else {}
        _engine = create_engine(
            database_url, future=True, pool_pre_ping=True, connect_args=connect_args
        )
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


def get_engine() -> Engine:
    """Return the initialized SQLAlchemy engine."""

    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_engine() first.")

    return _engine
