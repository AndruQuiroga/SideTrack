from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

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
    url = make_url(settings.db_url)
    if _AsyncSessionLocal is None or _current_url != str(url):
        # Build async engine using the configured URL as-is
        _async_engine = create_async_engine(str(url), pool_pre_ping=True)

        # Build a synchronous URL that uses a sync-capable driver for the same database
        # - For PostgreSQL, prefer psycopg (psycopg3) to avoid requiring psycopg2
        # - For SQLite, drop the "+aiosqlite" suffix
        # - Otherwise, fall back to the base driver without "+" extras
        drv = url.drivername
        if drv.startswith("postgresql"):
            sync_drivername = "postgresql+psycopg"
        elif drv.startswith("sqlite"):
            sync_drivername = "sqlite"
        else:
            sync_drivername = drv.split("+")[0]
        sync_url = url.set(drivername=sync_drivername)
        _sync_engine = create_engine(str(sync_url), pool_pre_ping=True)
        _AsyncSessionLocal = async_sessionmaker(
            bind=_async_engine, autoflush=False, autocommit=False
        )
        _SyncSessionLocal = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)
        _current_url = str(url)

        # expose synchronous engine globally for tests while keeping async engine for sessions
        globals()["engine"] = _sync_engine
        setattr(globals()["engine"], "sync_engine", _sync_engine)


def SessionLocal(async_session: bool | None = None) -> Session | AsyncSession:
    """Return a session appropriate for the current context.

    When ``async_session`` is ``True`` or ``False`` the return value is forced
    to be asynchronous or synchronous respectively, regardless of whether an
    event loop is running.  If ``None`` (the default) an ``AsyncSession`` is
    returned only when an event loop is active, otherwise a regular ``Session``
    is provided.  This avoids ``MissingGreenlet`` errors when synchronous code
    is executed from within an async test harness.
    """

    _get_sessionmakers()
    import asyncio

    if async_session is True:
        return _AsyncSessionLocal()
    if async_session is False:
        return _SyncSessionLocal()

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
        logger.warning("DB init failed", error=str(exc))


# initialize on module import
_get_sessionmakers()
