"""Tests for week CRUD and aggregates."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_list_weeks_empty(client):
    """GET /weeks returns an empty list when there are no weeks."""
    response = client.get("/weeks/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_create_week(client):
    """POST /weeks creates and returns a week."""
    payload = {"label": "WEEK 001 [2025-01-13]", "week_number": 1}
    response = client.post("/weeks/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == payload["label"]
    assert data["week_number"] == 1
    assert "id" in data
    assert data["nominations"] == []


@pytest.mark.unit
def test_create_week_idempotent(client):
    """Creating a week with the same label returns the existing record (upsert)."""
    payload = {"label": "WEEK 002", "week_number": 2}
    r1 = client.post("/weeks/", json=payload)
    r2 = client.post("/weeks/", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.unit
def test_get_week(client):
    """GET /weeks/{id} returns the week."""
    created = client.post("/weeks/", json={"label": "WEEK 003"}).json()
    response = client.get(f"/weeks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.unit
def test_get_week_not_found(client):
    """GET /weeks/{id} with a non-existent ID returns 404."""
    response = client.get("/weeks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.unit
def test_patch_week(client):
    """PATCH /weeks/{id} applies partial updates."""
    created = client.post("/weeks/", json={"label": "WEEK 004"}).json()
    patch_response = client.patch(
        f"/weeks/{created['id']}", json={"winner_album_id": None, "week_number": 4}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["week_number"] == 4


@pytest.mark.unit
def test_list_weeks_filter_has_winner(client):
    """GET /weeks?has_winner=true filters correctly."""
    client.post("/weeks/", json={"label": "No Winner Week"})
    # has_winner=true should return empty when no week has a winner
    response = client.get("/weeks/?has_winner=true")
    assert response.status_code == 200
    assert all(w["winner_album_id"] is not None for w in response.json())
