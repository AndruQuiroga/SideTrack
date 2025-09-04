from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .models import Base


settings = get_settings()
engine = create_engine(settings.db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def maybe_create_all():
    """Create tables automatically when using SQLite or when AUTO_MIGRATE is enabled.

    This makes the app functional without running Alembic in local/dev mode.
    """
    try:
        url = settings.db_url
        if settings.auto_migrate or url.startswith("sqlite"):  # type: ignore[attr-defined]
            Base.metadata.create_all(bind=engine)
    except Exception:
        # Silent fail to avoid blocking API start if DB isn't reachable yet (e.g., compose race)
        pass
