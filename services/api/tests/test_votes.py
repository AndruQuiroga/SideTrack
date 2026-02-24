"""Tests for vote creation and 409 on duplicate rank."""

from __future__ import annotations

import pytest


def _create_user(client, handle: str = "voter") -> dict:
    return client.post("/users/", json={"handle": handle, "display_name": "Voter"}).json()


def _create_album(client, title: str = "Vote Album") -> dict:
    return client.post("/albums/", json={"title": title, "artist_name": "Vote Artist"}).json()


def _setup_week_with_nomination(client, suffix: str = "") -> tuple[dict, dict, dict]:
    """Create a user, album, week, and nomination. Returns (week, nomination, user)."""
    user = _create_user(client, f"voter{suffix}")
    album = _create_album(client, f"Vote Album {suffix}")
    week = client.post("/weeks/", json={"label": f"VOTE WEEK {suffix}"}).json()
    nom = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"user_id": user["id"], "album_id": album["id"], "week_id": week["id"]},
    ).json()
    return week, nom, user


@pytest.mark.unit
def test_create_vote(client):
    """POST /weeks/{id}/votes creates a vote."""
    week, nom, user = _setup_week_with_nomination(client, "v1")
    payload = {
        "user_id": user["id"],
        "nomination_id": nom["id"],
        "week_id": week["id"],
        "rank": 1,
    }
    response = client.post(f"/weeks/{week['id']}/votes", json=payload)
    assert response.status_code == 201
    assert response.json()["rank"] == 1


@pytest.mark.unit
def test_duplicate_vote_rank_returns_409(client):
    """Submitting a vote with the same rank twice returns 409."""
    week, nom, user = _setup_week_with_nomination(client, "v2")
    payload = {
        "user_id": user["id"],
        "nomination_id": nom["id"],
        "week_id": week["id"],
        "rank": 1,
    }
    r1 = client.post(f"/weeks/{week['id']}/votes", json=payload)
    r2 = client.post(f"/weeks/{week['id']}/votes", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 409


@pytest.mark.unit
def test_invalid_rank_returns_400(client):
    """Ranks outside 1-2 return 400."""
    week, nom, user = _setup_week_with_nomination(client, "v3")
    payload = {
        "user_id": user["id"],
        "nomination_id": nom["id"],
        "week_id": week["id"],
        "rank": 3,
    }
    response = client.post(f"/weeks/{week['id']}/votes", json=payload)
    assert response.status_code == 400


@pytest.mark.unit
def test_two_different_ranks_allowed(client):
    """A user can cast both a 1st and 2nd choice vote."""
    week, nom, user = _setup_week_with_nomination(client, "v4")
    album2 = _create_album(client, "Album Two v4")
    nom2 = client.post(
        f"/weeks/{week['id']}/nominations",
        json={
            "user_id": _create_user(client, "nominator-v4")["id"],
            "album_id": album2["id"],
            "week_id": week["id"],
        },
    ).json()

    r1 = client.post(
        f"/weeks/{week['id']}/votes",
        json={"user_id": user["id"], "nomination_id": nom["id"], "week_id": week["id"], "rank": 1},
    )
    r2 = client.post(
        f"/weeks/{week['id']}/votes",
        json={"user_id": user["id"], "nomination_id": nom2["id"], "week_id": week["id"], "rank": 2},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
