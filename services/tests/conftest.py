from __future__ import annotations

import asyncio
import os
from pathlib import Path

import fakeredis
import pytest
import pytest_asyncio
import schedule
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from redis import Redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

ROOT = Path(__file__).resolve().parents[2]

# Configure a default SQLite database before importing the app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTO_MIGRATE"] = "1"

from sidetrack.api import main as app_main
from sidetrack.api.db import SessionLocal, get_db, maybe_create_all


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables for tests."""
    load_dotenv(ROOT / ".env.test", override=True)


@pytest.fixture
def db(tmp_path, request):
    """Configure database per test, using Postgres for integration tests."""
    if request.node.get_closest_marker("integration"):
        try:
            with PostgresContainer("postgres:16") as pg:
                url = pg.get_connection_url().replace(
                    "postgresql://", "postgresql+psycopg://"
                )
                os.environ["DATABASE_URL"] = url
                os.environ.setdefault("AUTO_MIGRATE", "1")
                asyncio.run(maybe_create_all())
                yield Path("/tmp/postgres")
        except Exception as exc:  # pragma: no cover - infrastructure failure
            pytest.skip(f"Postgres container unavailable: {exc}")
    else:
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
def redis_conn(request):
    if request.node.get_closest_marker("integration"):
        try:
            with RedisContainer("redis:7") as rc:
                conn = Redis.from_url(rc.get_connection_url())
                conn.flushall()
                try:
                    yield conn
                finally:
                    conn.flushall()
                    conn.close()
        except Exception as exc:  # pragma: no cover - infrastructure failure
            pytest.skip(f"Redis container unavailable: {exc}")
    else:
        conn = fakeredis.FakeRedis()
        conn.flushall()
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


@pytest_asyncio.fixture
async def async_client(db, redis_conn):
    """Return an AsyncClient with DB and Redis fixtures configured."""
    app_main._REDIS_CONN = redis_conn

    async def override_get_db():
        async with SessionLocal() as db_session:
            yield db_session

    app_main.app.dependency_overrides[get_db] = override_get_db

    async def _noop_create_all():
        return None

    app_main.maybe_create_all = _noop_create_all  # type: ignore

    async with app_main.app.router.lifespan_context(app_main.app):
        transport = ASGITransport(app=app_main.app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac

    app_main.app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_schedule():
    schedule.clear()
    yield
    schedule.clear()
