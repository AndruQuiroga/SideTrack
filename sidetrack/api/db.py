from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine

from sidetrack.common.models import Base

from .config import get_settings

logger = structlog.get_logger(__name__)

_async_engine = None
_sync_engine = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None
_SyncSessionLocal: sessionmaker[Session] | None = None
_current_url = None
engine = None


def _get_sessionmakers() -> None:
    global _async_engine, _sync_engine, _AsyncSessionLocal, _SyncSessionLocal, _current_url
    settings = get_settings()
    if _AsyncSessionLocal is None or _current_url != settings.db_url:
        _async_engine = create_async_engine(settings.db_url, pool_pre_ping=True)
        sync_url = settings.db_url.replace("+aiosqlite", "")
        _sync_engine = create_engine(sync_url, pool_pre_ping=True)
        _AsyncSessionLocal = async_sessionmaker(bind=_async_engine, autoflush=False, autocommit=False)
        _SyncSessionLocal = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)
        _current_url = settings.db_url

        # expose synchronous engine globally for tests while keeping async engine for sessions
        globals()["engine"] = _sync_engine
        setattr(globals()["engine"], "sync_engine", _sync_engine)


def SessionLocal() -> Session | AsyncSession:
    _get_sessionmakers()
    import asyncio

    try:
        asyncio.get_running_loop()
        return _AsyncSessionLocal()
    except RuntimeError:
        return _SyncSessionLocal()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _get_sessionmakers()
    db = _AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def maybe_create_all() -> None:
    """Create tables automatically when using SQLite or when AUTO_MIGRATE is enabled."""
    try:
        _get_sessionmakers()
        url = _current_url or ""
        if get_settings().auto_migrate or url.startswith("sqlite"):
            async with _async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as exc:
        logger.warning(
            "DB init failed", error=str(exc)
        )


# initialize on module import
_get_sessionmakers()

