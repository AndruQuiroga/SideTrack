"""Spec: platform/api-authorization, clients acting for users."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from sidetrack.club import Nomination, Vote
from sidetrack.identity.auth import ACT_AS_HEADER
from sidetrack.types import ClubRole

from .conftest import as_discord, as_user, snowflake

pytestmark = pytest.mark.unit


@pytest.fixture()
def week_with_nomination(client, admin, make_user):
    nominator = make_user("Nominator", role=ClubRole.MEMBER)
    album = client.post(
        "/albums/", json={"title": "LP", "artist_name": "Band"}, headers=as_user(nominator)
    ).json()
    week = client.post("/weeks/", json={"label": "Principal week"}, headers=as_user(admin)).json()
    nomination = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_user(nominator),
    ).json()
    return week, album, nomination


def test_web_acts_for_user(client, member):
    response = client.get(f"/users/{member.id}/linked-accounts", headers=as_user(member))
    assert response.status_code == 200


def test_bot_acts_for_discord_user(bot_client, client, admin, make_user, db):
    discord_id = snowflake()
    user = make_user("Discord member", role=ClubRole.MEMBER, discord_id=discord_id)
    week = client.post("/weeks/", json={"label": "Bot week"}, headers=as_user(admin)).json()
    album = bot_client.post(
        "/albums/", json={"title": "Bot LP", "artist_name": "Band"}, headers=as_discord(discord_id)
    ).json()

    response = bot_client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_discord(discord_id),
    )

    assert response.status_code == 201
    assert db.get(Nomination, response.json()["id"]).user_id == user.id


def test_bot_cannot_use_web_only_operation(bot_client, make_user):
    discord_id = snowflake()
    user = make_user("Discord member", role=ClubRole.MEMBER, discord_id=discord_id)
    response = bot_client.get(f"/users/{user.id}/linked-accounts", headers=as_discord(discord_id))
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


def test_wrong_subject_form_is_403(bot_client, admin):
    response = bot_client.post("/weeks/", json={"label": "Nope"}, headers=as_user(admin))
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


def test_web_cannot_act_as_discord(client):
    response = client.get("/weeks/", headers=as_discord(snowflake()))
    assert response.status_code == 403


def test_unknown_discord_subject_is_403(bot_client):
    response = bot_client.get("/weeks/", headers=as_discord(snowflake()))
    assert response.status_code == 403
    assert response.json()["error"] == "unknown_actor"


@pytest.mark.parametrize("value", ["user:not-a-uuid", "discord", "someone:1", "user:"])
def test_malformed_header_is_400(client, value):
    response = client.get("/weeks/", headers={ACT_AS_HEADER: value})
    assert response.status_code == 400
    assert response.json()["error"] == "bad_actor"


def test_body_user_mismatch(bot_client, make_user, week_with_nomination, db):
    week, _, nomination = week_with_nomination
    discord_id = snowflake()
    make_user("Voter", role=ClubRole.MEMBER, discord_id=discord_id)
    other = make_user("Other", role=ClubRole.MEMBER)

    response = bot_client.post(
        f"/weeks/{week['id']}/votes",
        json={
            "user_id": str(other.id),
            "nomination_id": nomination["id"],
            "week_id": week["id"],
            "rank": 1,
        },
        headers=as_discord(discord_id),
    )

    assert response.status_code == 403
    assert db.scalars(select(Vote)).all() == []


def test_body_user_omitted(client, admin, make_user, db):
    nominator = make_user("Nominator", role=ClubRole.MEMBER)
    album = client.post(
        "/albums/", json={"title": "Omitted", "artist_name": "Band"}, headers=as_user(nominator)
    ).json()
    week = client.post("/weeks/", json={"label": "Omitted week"}, headers=as_user(admin)).json()

    response = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_user(nominator),
    )

    assert response.status_code == 201
    assert db.get(Nomination, response.json()["id"]).user_id == nominator.id


def test_client_without_actor_cannot_write_for_users(client, week_with_nomination):
    week, _, nomination = week_with_nomination
    response = client.post(
        f"/weeks/{week['id']}/votes",
        json={"nomination_id": nomination["id"], "week_id": week["id"], "rank": 1},
    )
    assert response.status_code == 403
