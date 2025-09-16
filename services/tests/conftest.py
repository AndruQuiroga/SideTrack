from __future__ import annotations

import asyncio
import os
from pathlib import Path

import docker
import fakeredis
import fakeredis.aioredis
import pytest
import pytest_asyncio
import schedule
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from fastapi_limiter import FastAPILimiter
from httpx import ASGITransport, AsyncClient
from redis import Redis
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from sidetrack.config import get_settings

ROOT = Path(__file__).resolve().parents[2]

# Import application modules after fixtures set DATABASE_URL
from sidetrack.api import main as app_main
from sidetrack.api.db import get_db, maybe_create_all
from sidetrack.db import async_session_scope, session_scope


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable."""
    try:
        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    """Load environment variables for tests."""
    load_dotenv(ROOT / ".env.test", override=True)
    get_settings.cache_clear()


@pytest.fixture
def db(tmp_path, request):
    """Configure a Postgres database per test using testcontainers."""
    if not _docker_available():
        pytest.skip("Docker not available for Postgres tests")
    try:
        with PostgresContainer("postgres:16") as pg:
            url = pg.get_connection_url().replace("postgresql://", "postgresql+psycopg://")
            os.environ["DATABASE_URL"] = url
            os.environ.setdefault("AUTO_MIGRATE", "1")
            get_settings.cache_clear()
            asyncio.run(maybe_create_all())
            yield Path("/tmp/postgres")
    except Exception as exc:  # pragma: no cover - infrastructure failure
        pytest.skip(f"Postgres container unavailable: {exc}")


@pytest.fixture
def session(db):
    with session_scope() as sess:
        yield sess


@pytest_asyncio.fixture
async def async_session(db):
    async with async_session_scope() as sess:
        yield sess


@pytest.fixture
def redis_conn(request):
    if request.node.get_closest_marker("integration"):
        if not _docker_available():
            pytest.skip("Docker not available for integration tests")
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

    asyncio.run(FastAPILimiter.init(fakeredis.aioredis.FakeRedis()))

    def override_get_db():
        with session_scope() as db_session:
            yield db_session

    app_main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_main.app) as c:
        yield c
    app_main.app.dependency_overrides.clear()
    asyncio.run(FastAPILimiter.close())


@pytest_asyncio.fixture
async def async_client(db, redis_conn):
    """Return an AsyncClient with DB and Redis fixtures configured."""
    app_main._REDIS_CONN = redis_conn

    await FastAPILimiter.init(fakeredis.aioredis.FakeRedis())

    async def override_get_db():
        async with async_session_scope() as db_session:
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
    await FastAPILimiter.close()


@pytest.fixture(autouse=True)
def _clear_schedule():
    schedule.clear()
    yield
    schedule.clear()
