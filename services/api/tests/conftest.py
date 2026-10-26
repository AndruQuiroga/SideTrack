"""Shared test fixtures for the Sidetrack API test suite.

Tests run against PostgreSQL 16 + pgvector, the production image, built by
``alembic upgrade head`` (spec: platform/schema-migrations). Set
``SIDETRACK_TEST_DATABASE_URL`` to a throwaway database, or have Docker running so a
testcontainers instance is started for the session.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sidetrack.api.main import create_app
from sidetrack.club import upsert_member
from sidetrack.config import get_settings
from sidetrack.db import get_db
from sidetrack.identity import LinkedAccount, User
from sidetrack.identity.auth import ACT_AS_HEADER
from sidetrack.types import ClubRole, ProviderType

ROOT = Path(__file__).resolve().parents[3]
TEST_DB_IMAGE = "pgvector/pgvector:pg16"
TEST_WEB_TOKEN = "test-web-token"
TEST_BOT_TOKEN = "test-bot-token"
WEB = {"Authorization": f"Bearer {TEST_WEB_TOKEN}"}
BOT = {"Authorization": f"Bearer {TEST_BOT_TOKEN}"}
TEST_LINK_SECRET = "test-link-secret"


@pytest.fixture(autouse=True)
def api_settings(monkeypatch):
    """Pin settings so tests never depend on a developer's .env file."""
    monkeypatch.setenv("SIDETRACK_ENV", "production")
    monkeypatch.setenv("SIDETRACK_WEB_API_TOKEN", TEST_WEB_TOKEN)
    monkeypatch.setenv("SIDETRACK_BOT_API_TOKEN", TEST_BOT_TOKEN)
    monkeypatch.delenv("SIDETRACK_API_TOKEN", raising=False)
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


def as_user(user) -> dict[str, str]:
    """Headers for the web client acting for ``user`` (a User or its ID)."""
    user_id = getattr(user, "id", user)
    return {ACT_AS_HEADER: f"user:{user_id}"}


def as_discord(discord_id: str) -> dict[str, str]:
    """Headers for the bot client acting for a Discord user."""
    return {ACT_AS_HEADER: f"discord:{discord_id}"}


@pytest.fixture()
def client(app):
    """The web server's client, acting as itself unless a request adds ``as_user``."""
    with TestClient(app, headers=WEB) as test_client:
        yield test_client


@pytest.fixture()
def bot_client(app):
    """The Discord bot's client, acting as itself unless a request adds ``as_discord``."""
    with TestClient(app, headers=BOT) as test_client:
        yield test_client


@pytest.fixture()
def make_user(db):
    """Create a user directly; ``role`` makes them a club member, ``discord_id`` links Discord."""

    def factory(name="User", *, role: ClubRole | None = None, discord_id: str | None = None):
        user = User(display_name=name)
        db.add(user)
        db.flush()
        if discord_id is not None:
            db.add(
                LinkedAccount(
                    user_id=user.id, provider=ProviderType.DISCORD, provider_user_id=discord_id
                )
            )
        if role is not None:
            upsert_member(db, user.id, role)
        db.flush()
        return user

    return factory


@pytest.fixture()
def member(make_user):
    return make_user("Member", role=ClubRole.MEMBER)


@pytest.fixture()
def admin(make_user):
    return make_user("Admin", role=ClubRole.ADMIN)


def snowflake() -> str:
    return str(10**17 + uuid.uuid4().int % 10**17)


@pytest.fixture()
def anon_client(app):
    """Return a TestClient without credentials, like a browser."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
