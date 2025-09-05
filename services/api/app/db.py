from __future__ import annotations

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .models import Base


_engine = None
_SessionLocal = None
_current_url = None
engine = None


def _get_sessionmaker() -> sessionmaker:
    global _engine, _SessionLocal, _current_url
    settings = get_settings()
    if _SessionLocal is None or _current_url != settings.db_url:
        _engine = create_engine(settings.db_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        _current_url = settings.db_url
        globals()["engine"] = _engine
    return _SessionLocal


def SessionLocal():
    return _get_sessionmaker()()


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def maybe_create_all():
    """Create tables automatically when using SQLite or when AUTO_MIGRATE is enabled."""
    try:
        _get_sessionmaker()
        url = _current_url or ""
        if get_settings().auto_migrate or url.startswith("sqlite"):
            Base.metadata.create_all(bind=_engine)
    except Exception:
        # Silent fail to avoid blocking API start if DB isn't reachable yet (e.g., compose race)
        pass

# initialize on module import
_get_sessionmaker()
