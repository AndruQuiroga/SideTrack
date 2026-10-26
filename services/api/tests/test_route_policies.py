"""Spec: platform/api-authorization, route policies and authorization logging."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from fastapi import APIRouter

from sidetrack.api import main
from sidetrack.api.main import create_app
from sidetrack.identity.auth import PUBLIC_ROUTES, route_policies

from .conftest import BOT, TEST_BOT_TOKEN, as_user

pytestmark = pytest.mark.unit

DOC = Path(__file__).resolve().parents[3] / "docs" / "AUTHORIZATION.md"
ROW = re.compile(r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \| (.+?) \|")


def _documented() -> dict[tuple[str, str], str]:
    table: dict[tuple[str, str], str] = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            key = (match[1], match[2])
            assert key not in table, f"{key} is listed twice"
            table[key] = match[3].replace("\\|", "|").replace("`", "").strip()
    return table


def test_route_without_policy_fails_startup(monkeypatch):
    unclassified = APIRouter()

    @unclassified.get("/unclassified")
    def unclassified_route():
        return {}

    register = main.register_routes

    def register_with_extra(app):
        register(app)
        app.include_router(unclassified)

    monkeypatch.setattr(main, "register_routes", register_with_extra)
    with pytest.raises(RuntimeError, match="GET /unclassified"):
        create_app()


def test_policy_table_covers_the_api():
    actual = {
        key: ("public" if key in PUBLIC_ROUTES else " | ".join(scopes))
        for key, scopes in route_policies(create_app()).items()
        if key[0] != "HEAD"
    }
    assert _documented() == actual


def test_denied_request_is_logged_without_token(app, db, member, caplog):
    from fastapi.testclient import TestClient

    with TestClient(app, headers=BOT) as bot, caplog.at_level(logging.INFO):
        response = bot.get(f"/users/{member.id}/linked-accounts")
    assert response.status_code == 403
    request_id = response.headers["X-Request-ID"]
    lines = [r.getMessage() for r in caplog.records if request_id in r.getMessage()]
    assert any("client=bot" in line and "reason=forbidden" in line for line in lines)
    assert TEST_BOT_TOKEN not in caplog.text


def test_request_log_names_client_and_actor(client, member, caplog):
    with caplog.at_level(logging.INFO):
        response = client.get(f"/users/{member.id}", headers=as_user(member))
    assert response.status_code == 200
    assert f"client=web actor={member.id}" in caplog.text
