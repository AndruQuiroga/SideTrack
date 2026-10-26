"""Spec: platform/api-authorization (add-per-user-authorization) and error responses."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from sidetrack.api.main import create_app
from sidetrack.config import get_settings

from .conftest import BOT, TEST_BOT_TOKEN, TEST_WEB_TOKEN, as_user

pytestmark = pytest.mark.unit

WEEK = {"label": "Week 1"}


def test_startup_requires_each_client_token(monkeypatch):
    monkeypatch.delenv("SIDETRACK_BOT_API_TOKEN")
    monkeypatch.setenv("SIDETRACK_ENV", "production")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SIDETRACK_BOT_API_TOKEN") as error:
        create_app()
    assert TEST_WEB_TOKEN not in str(error.value)


def test_startup_defaults_to_production(monkeypatch):
    monkeypatch.delenv("SIDETRACK_WEB_API_TOKEN")
    monkeypatch.delenv("SIDETRACK_ENV")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SIDETRACK_WEB_API_TOKEN"):
        create_app()


def test_startup_rejects_duplicate_tokens(monkeypatch):
    monkeypatch.setenv("SIDETRACK_BOT_API_TOKEN", TEST_WEB_TOKEN)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="distinct"):
        create_app()


def test_startup_allows_missing_tokens_in_development(monkeypatch, caplog, db):
    monkeypatch.delenv("SIDETRACK_WEB_API_TOKEN")
    monkeypatch.setenv("SIDETRACK_ENV", "development")
    get_settings.cache_clear()

    with caplog.at_level(logging.WARNING):
        app = create_app()
    assert "cannot call the API" in caplog.text

    from sidetrack.db import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        # Development mode does not open the API: unknown callers still get 401.
        assert client.get("/weeks/").status_code == 401
        assert client.get("/weeks/", headers=BOT).status_code == 200


def test_anonymous_read_is_401(anon_client):
    response = anon_client.get("/weeks/")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_write_without_token_is_401(anon_client):
    assert anon_client.post("/weeks/", json=WEEK).status_code == 401


def test_unknown_token_is_401(anon_client, member):
    response = anon_client.get(
        f"/users/{member.id}/listening/recent",
        headers={"Authorization": f"Bearer {TEST_BOT_TOKEN}x"},
    )
    assert response.status_code == 401


def test_shared_token_is_rejected(anon_client, monkeypatch):
    # The retired shared token grants nothing, even if still present in the environment.
    monkeypatch.setenv("SIDETRACK_API_TOKEN", "old-shared-token")
    response = anon_client.get("/weeks/", headers={"Authorization": "Bearer old-shared-token"})
    assert response.status_code == 401


def test_health_stays_public(anon_client):
    assert anon_client.get("/health").status_code != 401


def test_preflight_allows_no_browser_origin(anon_client):
    response = anon_client.options(
        "/weeks/",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_correct_token_and_actor_succeed(client, admin):
    assert client.post("/weeks/", json=WEEK, headers=as_user(admin)).status_code == 201


def test_unhandled_error_hides_internals(app, caplog):
    secret_url = "postgresql://sidetrack:hunter2@db:5432/sidetrack"

    @app.get("/test-boom")
    def boom():
        raise RuntimeError(f"could not connect to {secret_url}")

    with TestClient(app, raise_server_exceptions=False, headers=BOT) as client:
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


def test_valid_incoming_request_id_is_echoed(anon_client):
    response = anon_client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_invalid_incoming_request_id_is_replaced(anon_client):
    response = anon_client.get("/health", headers={"X-Request-ID": "bad id; drop"})
    assert response.headers["X-Request-ID"] != "bad id; drop"
