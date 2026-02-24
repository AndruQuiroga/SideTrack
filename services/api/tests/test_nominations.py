"""Tests for nomination creation and filtering."""

from __future__ import annotations

import pytest


def _create_user(client, handle: str = "testuser") -> dict:
    return client.post("/users/", json={"handle": handle, "display_name": "Test User"}).json()


def _create_album(client, title: str = "Test Album") -> dict:
    return client.post("/albums/", json={"title": title, "artist_name": "Test Artist"}).json()


def _create_week(client, label: str = "WEEK 001") -> dict:
    return client.post("/weeks/", json={"label": label}).json()


@pytest.mark.unit
def test_create_nomination(client):
    """POST /weeks/{week_id}/nominations creates a nomination."""
    user = _create_user(client)
    album = _create_album(client)
    week = _create_week(client)

    payload = {
        "user_id": user["id"],
        "album_id": album["id"],
        "week_id": week["id"],
        "pitch": "Great album!",
        "genre": "Indie Rock",
    }
    response = client.post(f"/weeks/{week['id']}/nominations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["album_id"] == album["id"]
    assert data["user_id"] == user["id"]


@pytest.mark.unit
def test_duplicate_nomination_returns_409(client):
    """Submitting the same nomination twice returns 409 Conflict."""
    user = _create_user(client, "user-conflict")
    album = _create_album(client, "Conflict Album")
    week = _create_week(client, "WEEK CONFLICT")

    payload = {
        "user_id": user["id"],
        "album_id": album["id"],
        "week_id": week["id"],
    }
    r1 = client.post(f"/weeks/{week['id']}/nominations", json=payload)
    r2 = client.post(f"/weeks/{week['id']}/nominations", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 409


@pytest.mark.unit
def test_list_nominations_filter_by_week(client):
    """GET /nominations?week_id returns only nominations for that week."""
    user = _create_user(client, "filter-user")
    album = _create_album(client, "Filter Album")
    week_a = _create_week(client, "WEEK A")
    week_b = _create_week(client, "WEEK B")

    payload = {"user_id": user["id"], "album_id": album["id"], "week_id": week_a["id"]}
    client.post(f"/weeks/{week_a['id']}/nominations", json=payload)

    response = client.get(f"/nominations/?week_id={week_b['id']}")
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(f"/nominations/?week_id={week_a['id']}")
    assert response.status_code == 200
    assert len(response.json()) == 1
