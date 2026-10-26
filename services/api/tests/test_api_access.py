"""Spec: platform/api-access (openspec/changes/harden-api-credentials)."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from services.api.config import get_settings
from services.api.main import create_app

from .conftest import TEST_API_TOKEN

pytestmark = pytest.mark.unit

WEEK = {"label": "Week 1"}


def test_startup_requires_token_in_production(monkeypatch):
    monkeypatch.delenv("SIDETRACK_API_TOKEN")
    monkeypatch.setenv("SIDETRACK_ENV", "production")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SIDETRACK_API_TOKEN"):
        create_app()


def test_startup_defaults_to_production(monkeypatch):
    monkeypatch.delenv("SIDETRACK_API_TOKEN")
    monkeypatch.delenv("SIDETRACK_ENV")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SIDETRACK_API_TOKEN"):
        create_app()


def test_startup_allows_missing_token_in_development(monkeypatch, caplog, db):
    monkeypatch.delenv("SIDETRACK_API_TOKEN")
    monkeypatch.setenv("SIDETRACK_ENV", "development")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING):
        app = create_app()
    assert "writes are unauthenticated" in caplog.text

    from services.api.db import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        assert client.post("/weeks/", json=WEEK).status_code == 201


def test_write_without_token_is_401(anon_client):
    response = anon_client.post("/weeks/", json=WEEK)
    assert response.status_code == 401
    assert anon_client.get("/weeks/").json() == []


def test_write_with_wrong_token_is_401(anon_client):
    response = anon_client.post(
        "/weeks/", json=WEEK, headers={"Authorization": f"Bearer {TEST_API_TOKEN}x"}
    )
    assert response.status_code == 401


def test_write_with_token_succeeds(client):
    assert client.post("/weeks/", json=WEEK).status_code == 201


def test_unhandled_error_hides_internals(app, caplog):
    secret_url = "postgresql://sidetrack:hunter2@db:5432/sidetrack"

    @app.get("/test-boom")
    def boom():
        raise RuntimeError(f"could not connect to {secret_url}")

    with TestClient(app, raise_server_exceptions=False) as client:
        with caplog.at_level(logging.ERROR):
            response = client.get("/test-boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    request_id = body["request_id"]
    assert request_id
    assert secret_url not in response.text
    assert "hunter2" not in response.text
    assert response.headers["X-Request-ID"] == request_id
    assert f"request_id={request_id}" in caplog.text
    assert secret_url in caplog.text


def test_valid_incoming_request_id_is_echoed(client):
    response = client.get("/weeks/", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_invalid_incoming_request_id_is_replaced(client):
    response = client.get("/weeks/", headers={"X-Request-ID": "bad id; drop"})
    assert response.headers["X-Request-ID"] != "bad id; drop"
