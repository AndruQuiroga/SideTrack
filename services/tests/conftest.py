from __future__ import annotations

import asyncio
import os
from pathlib import Path

import fakeredis
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from sidetrack.api import main as app_main
from sidetrack.api.db import SessionLocal, get_db, maybe_create_all

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables for tests."""
    load_dotenv(ROOT / ".env.test", override=True)


@pytest.fixture
def db(tmp_path):
    """Configure a temporary SQLite database for each test."""
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    os.environ.setdefault("AUTO_MIGRATE", "1")
    asyncio.run(maybe_create_all())
    yield db_file
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def session(db):
    with SessionLocal() as sess:
        yield sess


@pytest_asyncio.fixture
async def async_session(db):
    async with SessionLocal() as sess:
        yield sess


@pytest.fixture
def redis_conn():
    conn = fakeredis.FakeRedis()
    try:
        yield conn
    finally:
        conn.flushall()
        conn.close()


@pytest.fixture
def client(db, redis_conn):
    """Return a TestClient with DB and Redis fixtures configured."""
    app_main._REDIS_CONN = redis_conn

    def override_get_db():
        with SessionLocal() as db_session:
            yield db_session

    app_main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_main.app) as c:
        yield c
    app_main.app.dependency_overrides.clear()
