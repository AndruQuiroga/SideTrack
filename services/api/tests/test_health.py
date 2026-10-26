"""Spec: platform/health (openspec/changes/deploy-on-stache-rack)."""

from __future__ import annotations

import time

import pytest

import services.api.main as main_module

pytestmark = pytest.mark.unit

DB_URL = "postgresql+psycopg://sidetrack:hunter2@db:5432/sidetrack"


def test_health_ok(anon_client, monkeypatch):
    monkeypatch.setattr(main_module, "check_database", lambda: None)

    response = anon_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "details": {"database": "ok"}}


def test_health_db_down_is_503(anon_client, monkeypatch):
    def failing() -> None:
        raise ConnectionError(f"could not connect to {DB_URL}")

    monkeypatch.setattr(main_module, "check_database", failing)

    response = anon_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "details": {"database": "unreachable"}}
    assert "hunter2" not in response.text
    assert DB_URL not in response.text


def test_health_times_out_fast(anon_client, monkeypatch):
    monkeypatch.setattr(main_module, "HEALTH_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(main_module, "check_database", lambda: time.sleep(1.0))

    started = time.monotonic()
    response = anon_client.get("/health")

    assert response.status_code == 503
    assert time.monotonic() - started < 0.9


def test_health_default_timeout_is_two_seconds():
    assert main_module.HEALTH_TIMEOUT_SECONDS == 2.0
