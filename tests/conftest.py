"""Reuse the migrated-Postgres API fixtures for architecture integration tests."""

from services.api.tests.conftest import (  # noqa: F401
    anon_client,
    api_settings,
    app,
    client,
    database_url,
    db,
    engine,
)
