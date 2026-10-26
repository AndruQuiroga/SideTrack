"""Reuse the migrated-Postgres API fixtures for architecture integration tests."""

from services.api.tests.conftest import (  # noqa: F401
    admin,
    anon_client,
    api_settings,
    app,
    bot_client,
    client,
    database_url,
    db,
    engine,
    make_user,
    member,
)
