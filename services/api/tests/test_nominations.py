"""Tests for nomination creation and filtering. Members nominate as themselves."""

from __future__ import annotations

import pytest

from sidetrack.types import ClubRole

from .conftest import as_user


def _create_album(client, actor, title: str = "Test Album") -> dict:
    return client.post(
        "/albums/", json={"title": title, "artist_name": "Test Artist"}, headers=as_user(actor)
    ).json()


def _create_week(client, admin, label: str = "WEEK 001") -> dict:
    return client.post("/weeks/", json={"label": label}, headers=as_user(admin)).json()


@pytest.mark.unit
def test_create_nomination(client, admin, make_user):
    """POST /weeks/{week_id}/nominations creates a nomination."""
    user = make_user("Test User", role=ClubRole.MEMBER)
    album = _create_album(client, user)
    week = _create_week(client, admin)

    payload = {
        "user_id": str(user.id),
        "album_id": album["id"],
        "week_id": week["id"],
        "pitch": "Great album!",
        "genre": "Indie Rock",
    }
    response = client.post(f"/weeks/{week['id']}/nominations", json=payload, headers=as_user(user))
    assert response.status_code == 201
    data = response.json()
    assert data["album_id"] == album["id"]
    assert data["user_id"] == str(user.id)


@pytest.mark.unit
def test_duplicate_nomination_returns_409(client, admin, member):
    """Submitting the same nomination twice returns 409 Conflict."""
    album = _create_album(client, member, "Conflict Album")
    week = _create_week(client, admin, "WEEK CONFLICT")

    payload = {"album_id": album["id"], "week_id": week["id"]}
    r1 = client.post(f"/weeks/{week['id']}/nominations", json=payload, headers=as_user(member))
    r2 = client.post(f"/weeks/{week['id']}/nominations", json=payload, headers=as_user(member))
    assert r1.status_code == 201
    assert r2.status_code == 409


@pytest.mark.unit
def test_list_nominations_filter_by_week(client, admin, member):
    """GET /nominations?week_id returns only nominations for that week."""
    album = _create_album(client, member, "Filter Album")
    week_a = _create_week(client, admin, "WEEK A")
    week_b = _create_week(client, admin, "WEEK B")

    payload = {"album_id": album["id"], "week_id": week_a["id"]}
    client.post(f"/weeks/{week_a['id']}/nominations", json=payload, headers=as_user(member))

    response = client.get(f"/nominations/?week_id={week_b['id']}", headers=as_user(member))
    assert response.status_code == 200
    assert response.json() == []

    response = client.get(f"/nominations/?week_id={week_a['id']}", headers=as_user(member))
    assert response.status_code == 200
    assert len(response.json()) == 1
