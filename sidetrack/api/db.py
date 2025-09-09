from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Tuple

import structlog
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
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
_current_key: str | None = None
engine = None


def _derive_urls(base_url: URL) -> Tuple[URL, URL]:
    """Return (async_url, sync_url) derived from a base URL.

    Supports PostgreSQL only:
    - async = postgresql+asyncpg
    - sync  = postgresql+psycopg

    Raises ValueError for SQLite or other unsupported schemes.
    """
    drv = base_url.drivername
    if drv.startswith("postgresql"):
        return (
            base_url.set(drivername="postgresql+asyncpg"),
            base_url.set(drivername="postgresql+psycopg"),
        )
    if drv.startswith("sqlite"):
        raise ValueError("SQLite is not supported. Use PostgreSQL.")
    raise ValueError(f"Unsupported database driver: {drv}")


def _dsn_key(url: URL) -> str:
    """Return a key that changes whenever any credential or host detail changes.

    Important: Do NOT mask the password here — we want engine/sessionmakers to
    be reinitialized when only the password changes. Password is masked only in logs.
    """
    return str(url)


def _init_engines() -> None:
    global _async_engine, _sync_engine, _AsyncSessionLocal, _SyncSessionLocal, _current_key, engine

    settings = get_settings()
    base_url = make_url(settings.db_url)
    async_url, sync_url = _derive_urls(base_url)
    key = _dsn_key(base_url)

    if _AsyncSessionLocal is not None and _current_key == key:
        return

    # Dispose previous engines if any
    try:
        if _async_engine is not None:
            _async_engine.sync_engine.dispose()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass
    try:
        if _sync_engine is not None:
            _sync_engine.dispose()
    except Exception:  # pragma: no cover
        pass

    _async_engine = create_async_engine(async_url, pool_pre_ping=True)
    _sync_engine = create_engine(sync_url, pool_pre_ping=True)
    _AsyncSessionLocal = async_sessionmaker(bind=_async_engine, autoflush=False, autocommit=False)
    _SyncSessionLocal = sessionmaker(bind=_sync_engine, autoflush=False, autocommit=False)
    _current_key = key

    # Expose sync engine for tests
    engine = _sync_engine
    globals()["engine"] = _sync_engine

    # Log configured URLs (masked)
    try:
        logger.info(
            "DB configured",
            base=base_url.render_as_string(hide_password=True),
            async_url=async_url.render_as_string(hide_password=True),
            sync_url=sync_url.render_as_string(hide_password=True),
        )
    except Exception:  # pragma: no cover
        logger.info(
            "DB configured",
            base=str(base_url),
            async_url=str(async_url),
            sync_url=str(sync_url),
        )


def SessionLocal(async_session: bool | None = None) -> Session | AsyncSession:
    """Return a session appropriate for the current context.

    - async_session=True  -> always AsyncSession
    - async_session=False -> always sync Session
    - async_session=None  -> AsyncSession when an event loop is running, else sync Session
    """
    _init_engines()
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
    _init_engines()
    db = _AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def maybe_create_all() -> None:
    """Create tables automatically when AUTO_MIGRATE is enabled."""
    try:
        _init_engines()
        settings = get_settings()
        base_url = make_url(settings.db_url)
        if settings.auto_migrate:
            async with _async_engine.begin():
                await _async_engine.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as exc:
        logger.warning("DB init failed", error=str(exc))


# Do not initialize engines at import time; defer to first usage.
