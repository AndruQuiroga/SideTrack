"""Spec: platform/runtime-config (openspec/changes/deploy-on-stache-rack)."""

from __future__ import annotations

import logging

import pytest

from sidetrack.api.main import create_app
from sidetrack.config import get_settings

pytestmark = pytest.mark.unit


@pytest.fixture()
def secrets_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SIDETRACK_SECRETS_DIR", str(tmp_path))
    get_settings.cache_clear()
    return tmp_path


def test_secret_file_used(secrets_dir, monkeypatch):
    (secrets_dir / "sidetrack_api_token").write_text("abc")
    monkeypatch.delenv("SIDETRACK_API_TOKEN")

    assert get_settings().api_token == "abc"


def test_env_overrides_secret_file(secrets_dir, monkeypatch):
    (secrets_dir / "sidetrack_api_token").write_text("abc")
    monkeypatch.setenv("SIDETRACK_API_TOKEN", "xyz")

    assert get_settings().api_token == "xyz"


def test_trailing_newline_stripped(secrets_dir, monkeypatch):
    (secrets_dir / "sidetrack_api_token").write_text("abc\n")
    (secrets_dir / "database_url").write_text("postgresql+psycopg://u:p@db:5432/sidetrack\r\n")
    monkeypatch.delenv("SIDETRACK_API_TOKEN")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = get_settings()
    assert settings.api_token == "abc"
    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/sidetrack"


def test_missing_secrets_dir_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("SIDETRACK_SECRETS_DIR", str(tmp_path / "absent"))
    get_settings.cache_clear()

    assert get_settings().api_token == "test-api-token"


def test_secrets_are_masked_in_repr():
    settings = get_settings()
    assert "test-api-token" not in repr(settings)
    assert "test-link-secret" not in repr(settings)


def test_startup_log_redacts_password(monkeypatch, caplog):
    import sidetrack.db as db_module

    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://sidetrack:hunter2@db.internal:5432/club"
    )
    monkeypatch.setattr(db_module, "_engine", None)
    monkeypatch.setattr(db_module, "_SessionLocal", None)
    get_settings.cache_clear()

    with caplog.at_level(logging.INFO, logger="sidetrack.api.main"):
        create_app()

    assert "db.internal:5432/club" in caplog.text
    assert "hunter2" not in caplog.text
