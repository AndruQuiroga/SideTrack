from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.common.models import Base

from .config import get_settings

logger = structlog.get_logger(__name__)

_engine = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None
_current_url = None
engine = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _SessionLocal, _current_url
    settings = get_settings()
    if _SessionLocal is None or _current_url != settings.db_url:
        _engine = create_async_engine(settings.db_url, pool_pre_ping=True)
        SQLAlchemyInstrumentor().instrument(engine=_engine)
        _SessionLocal = async_sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        _current_url = settings.db_url
        globals()["engine"] = _engine
    return _SessionLocal


def SessionLocal() -> AsyncSession:
    return _get_sessionmaker()()


@asynccontextmanager
async def get_db() -> AsyncSession:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


async def maybe_create_all() -> None:
    """Create tables automatically when using SQLite or when AUTO_MIGRATE is enabled."""
    try:
        _get_sessionmaker()
        url = _current_url or ""
        if get_settings().auto_migrate or url.startswith("sqlite"):
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as exc:
        logger.warning(
            "DB init failed", error=str(exc)
        )


# initialize on module import
_get_sessionmaker()

