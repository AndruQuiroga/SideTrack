"""Tests for vote creation and 409 on duplicate rank. Members vote as themselves."""

from __future__ import annotations

import pytest

from sidetrack.types import ClubRole

from .conftest import as_user


def _create_album(client, actor, title: str = "Vote Album") -> dict:
    return client.post(
        "/albums/", json={"title": title, "artist_name": "Vote Artist"}, headers=as_user(actor)
    ).json()


@pytest.fixture()
def setup(client, admin, make_user):
    """Create a voter, album, week and nomination. Returns (week, nomination, voter)."""

    def build(suffix: str = ""):
        voter = make_user(f"voter{suffix}", role=ClubRole.MEMBER)
        album = _create_album(client, voter, f"Vote Album {suffix}")
        week = client.post(
            "/weeks/", json={"label": f"VOTE WEEK {suffix}"}, headers=as_user(admin)
        ).json()
        nom = client.post(
            f"/weeks/{week['id']}/nominations",
            json={"album_id": album["id"], "week_id": week["id"]},
            headers=as_user(voter),
        ).json()
        return week, nom, voter

    return build


@pytest.mark.unit
def test_create_vote(client, setup):
    """POST /weeks/{id}/votes creates a vote."""
    week, nom, user = setup("v1")
    payload = {
        "user_id": str(user.id),
        "nomination_id": nom["id"],
        "week_id": week["id"],
        "rank": 1,
    }
    response = client.post(f"/weeks/{week['id']}/votes", json=payload, headers=as_user(user))
    assert response.status_code == 201
    assert response.json()["rank"] == 1


@pytest.mark.unit
def test_duplicate_vote_rank_returns_409(client, setup):
    """Submitting a vote with the same rank twice returns 409."""
    week, nom, user = setup("v2")
    payload = {"nomination_id": nom["id"], "week_id": week["id"], "rank": 1}
    r1 = client.post(f"/weeks/{week['id']}/votes", json=payload, headers=as_user(user))
    r2 = client.post(f"/weeks/{week['id']}/votes", json=payload, headers=as_user(user))
    assert r1.status_code == 201
    assert r2.status_code == 409


@pytest.mark.unit
def test_invalid_rank_returns_400(client, setup):
    """Ranks outside 1-2 return 400."""
    week, nom, user = setup("v3")
    payload = {"nomination_id": nom["id"], "week_id": week["id"], "rank": 3}
    response = client.post(f"/weeks/{week['id']}/votes", json=payload, headers=as_user(user))
    assert response.status_code == 400


@pytest.mark.unit
def test_two_different_ranks_allowed(client, setup, make_user):
    """A user can cast both a 1st and 2nd choice vote."""
    week, nom, user = setup("v4")
    nominator = make_user("nominator-v4", role=ClubRole.MEMBER)
    album2 = _create_album(client, nominator, "Album Two v4")
    nom2 = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album2["id"], "week_id": week["id"]},
        headers=as_user(nominator),
    ).json()

    r1 = client.post(
        f"/weeks/{week['id']}/votes",
        json={"nomination_id": nom["id"], "week_id": week["id"], "rank": 1},
        headers=as_user(user),
    )
    r2 = client.post(
        f"/weeks/{week['id']}/votes",
        json={"nomination_id": nom2["id"], "week_id": week["id"], "rank": 2},
        headers=as_user(user),
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
