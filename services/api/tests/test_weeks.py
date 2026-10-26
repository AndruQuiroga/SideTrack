"""Tests for week CRUD and aggregates. Weeks are created by club admins."""

from __future__ import annotations

import pytest

from .conftest import as_user


@pytest.mark.unit
def test_list_weeks_empty(client, member):
    """GET /weeks returns an empty list when there are no weeks."""
    response = client.get("/weeks/", headers=as_user(member))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_create_week(client, admin):
    """POST /weeks creates and returns a week."""
    payload = {"label": "WEEK 001 [2025-01-13]", "week_number": 1}
    response = client.post("/weeks/", json=payload, headers=as_user(admin))
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == payload["label"]
    assert data["week_number"] == 1
    assert "id" in data
    assert data["nominations"] == []


@pytest.mark.unit
def test_create_week_idempotent(client, admin):
    """Creating a week with the same label returns the existing record (upsert)."""
    payload = {"label": "WEEK 002", "week_number": 2}
    r1 = client.post("/weeks/", json=payload, headers=as_user(admin))
    r2 = client.post("/weeks/", json=payload, headers=as_user(admin))
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.unit
def test_get_week(client, admin):
    """GET /weeks/{id} returns the week."""
    created = client.post("/weeks/", json={"label": "WEEK 003"}, headers=as_user(admin)).json()
    response = client.get(f"/weeks/{created['id']}", headers=as_user(admin))
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.unit
def test_get_week_not_found(client, member):
    """GET /weeks/{id} with a non-existent ID returns 404."""
    response = client.get("/weeks/00000000-0000-0000-0000-000000000000", headers=as_user(member))
    assert response.status_code == 404


@pytest.mark.unit
def test_patch_week(client, admin):
    """PATCH /weeks/{id} applies partial updates."""
    created = client.post("/weeks/", json={"label": "WEEK 004"}, headers=as_user(admin)).json()
    patch_response = client.patch(
        f"/weeks/{created['id']}",
        json={"winner_album_id": None, "week_number": 4},
        headers=as_user(admin),
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["week_number"] == 4


@pytest.mark.unit
def test_list_weeks_filter_has_winner(client, admin):
    """GET /weeks?has_winner=true filters correctly."""
    client.post("/weeks/", json={"label": "No Winner Week"}, headers=as_user(admin))
    # has_winner=true should return empty when no week has a winner
    response = client.get("/weeks/?has_winner=true", headers=as_user(admin))
    assert response.status_code == 200
    assert all(w["winner_album_id"] is not None for w in response.json())
