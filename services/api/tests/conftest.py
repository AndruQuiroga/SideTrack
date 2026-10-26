"""Shared test fixtures for the Sidetrack API test suite.

Tests run against PostgreSQL 16 + pgvector, the production image, built by
``alembic upgrade head`` (spec: platform/schema-migrations). Set
``SIDETRACK_TEST_DATABASE_URL`` to a throwaway database, or have Docker running so a
testcontainers instance is started for the session.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.api.config import get_settings
from services.api.db import get_db
from services.api.main import create_app

ROOT = Path(__file__).resolve().parents[3]
TEST_DB_IMAGE = "pgvector/pgvector:pg16"
TEST_API_TOKEN = "test-api-token"
TEST_LINK_SECRET = "test-link-secret"


@pytest.fixture(autouse=True)
def api_settings(monkeypatch):
    """Pin settings so tests never depend on a developer's .env file."""
    monkeypatch.setenv("SIDETRACK_ENV", "production")
    monkeypatch.setenv("SIDETRACK_API_TOKEN", TEST_API_TOKEN)
    monkeypatch.setenv("SIDETRACK_LINK_SECRET", TEST_LINK_SECRET)
    monkeypatch.setenv("LASTFM_API_KEY", "test-lastfm-key")
    monkeypatch.setenv("LASTFM_API_SECRET", "test-lastfm-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def database_url():
    """A throwaway Postgres database for the whole session."""
    url = os.environ.get("SIDETRACK_TEST_DATABASE_URL")
    if url:
        yield url
        return

    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer(TEST_DB_IMAGE, driver="psycopg")
        container.start()
    except Exception as exc:  # Docker missing or not running
        pytest.exit(
            "No test database. Start Docker, or set SIDETRACK_TEST_DATABASE_URL to a throwaway "
            f"Postgres 16 database. ({exc.__class__.__name__}: {exc})",
            returncode=1,
        )
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


def migrate(database_url: str, revision: str = "head") -> None:
    """Run Alembic migrations against ``database_url``.

    Uses a file-less Config so env.py doesn't call ``fileConfig``, which would disable
    the loggers that tests capture.
    """
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def engine(database_url):
    """Engine for a database migrated to head."""
    migrate(database_url)
    engine = create_engine(database_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine):
    """A session inside a transaction that is rolled back after each test.

    Route-level commit()/rollback() operate on savepoints, so tests can't leak state.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def app(db):
    """Return the API app with the DB session overridden to use the test DB."""
    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture()
def client(app):
    """Return a TestClient that sends the service token, like the bot and web server."""
    with TestClient(app, headers={"Authorization": f"Bearer {TEST_API_TOKEN}"}) as test_client:
        yield test_client


@pytest.fixture()
def anon_client(app):
    """Return a TestClient without credentials, like a browser."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
