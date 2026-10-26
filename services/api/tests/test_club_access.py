"""Spec: club/membership-access, who may read and change club data."""

from __future__ import annotations

import pytest

from sidetrack.club import Nomination
from sidetrack.types import ClubRole

from .conftest import as_discord, as_user, snowflake

pytestmark = pytest.mark.unit


@pytest.fixture()
def week(client, admin):
    return client.post("/weeks/", json={"label": "Access week"}, headers=as_user(admin)).json()


def _album(client, actor, title="Club LP"):
    return client.post(
        "/albums/", json={"title": title, "artist_name": "Band"}, headers=as_user(actor)
    ).json()


def _nominate(client, actor, week, title="Club LP"):
    album = _album(client, actor, title)
    return client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_user(actor),
    ).json()


def test_member_reads_week(client, member, week):
    response = client.get(f"/weeks/{week['id']}", headers=as_user(member))
    assert response.status_code == 200
    assert response.json()["nominations"] == []


@pytest.mark.parametrize(
    "path", ["/weeks/", "/nominations/", "/ratings", "/trending", "/feed", "/users/"]
)
def test_signed_in_non_member_is_refused(client, make_user, path):
    outsider = make_user("Outsider")
    response = client.get(path, headers=as_user(outsider))
    assert response.status_code == 403
    assert response.json()["error"] == "not_a_club_member"


def test_left_member_loses_access(client, member, week, db):
    from sidetrack.club import mark_left

    mark_left(db, member.id)
    response = client.get(f"/weeks/{week['id']}", headers=as_user(member))
    assert response.json()["error"] == "not_a_club_member"


def test_bot_as_itself_reads_weeks(bot_client, week):
    assert bot_client.get("/weeks/").status_code == 200


def test_non_member_cannot_nominate(client, make_user, week, member, db):
    outsider = make_user("Outsider")
    album = _album(client, member)
    response = client.post(
        f"/weeks/{week['id']}/nominations",
        json={"album_id": album["id"], "week_id": week["id"]},
        headers=as_user(outsider),
    )
    assert response.status_code == 403
    assert db.query(Nomination).count() == 0


def test_member_cannot_edit_someone_elses_nomination(client, make_user, week, db):
    nominator = make_user("Nominator", role=ClubRole.MEMBER)
    other = make_user("Other", role=ClubRole.MEMBER)
    nomination = _nominate(client, nominator, week)

    response = client.patch(
        f"/nominations/{nomination['id']}", json={"pitch": "Mine now"}, headers=as_user(other)
    )

    assert response.status_code == 403
    db.expire_all()
    assert db.get(Nomination, nomination["id"]).pitch is None


def test_nominator_edits_own_nomination(client, member, week):
    nomination = _nominate(client, member, week)
    response = client.patch(
        f"/nominations/{nomination['id']}", json={"pitch": "Listen"}, headers=as_user(member)
    )
    assert response.status_code == 200
    assert response.json()["pitch"] == "Listen"


def test_admin_withdraws_a_nomination(client, admin, member, week, db):
    nomination = _nominate(client, member, week)
    response = client.delete(f"/nominations/{nomination['id']}", headers=as_user(admin))
    assert response.status_code == 204
    db.expire_all()
    assert db.get(Nomination, nomination["id"]) is None


def test_member_cannot_create_week(client, member):
    response = client.post("/weeks/", json={"label": "Rogue"}, headers=as_user(member))
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"


def test_admin_overrides_winner(client, admin, week):
    album = _album(client, admin, "Admin pick")
    response = client.post(
        f"/admin/weeks/{week['id']}/override-winner",
        json={"album_id": album["id"]},
        headers=as_user(admin),
    )
    assert response.status_code == 200
    assert response.json()["winner_album_id"] == album["id"]


def test_member_cannot_override_winner(client, member, week):
    album = _album(client, member, "Member pick")
    response = client.post(
        f"/admin/weeks/{week['id']}/override-winner",
        json={"album_id": album["id"]},
        headers=as_user(member),
    )
    assert response.status_code == 403


def test_member_cannot_edit_album(client, member):
    album = _album(client, member)
    response = client.patch(
        f"/albums/{album['id']}", json={"title": "Renamed"}, headers=as_user(member)
    )
    assert response.status_code == 403


def test_bot_sets_thread_id(bot_client, week):
    response = bot_client.patch(f"/weeks/{week['id']}", json={"nominations_thread_id": "987"})
    assert response.status_code == 200
    assert response.json()["nominations_thread_id"] == "987"


def test_bot_cannot_change_deadline_without_actor(bot_client, week):
    response = bot_client.patch(
        f"/weeks/{week['id']}", json={"poll_close_at": "2030-01-01T00:00:00Z"}
    )
    assert response.status_code == 403
    assert bot_client.get(f"/weeks/{week['id']}").json()["poll_close_at"] is None


def test_bot_acting_for_admin_manages_week(bot_client, make_user):
    discord_id = snowflake()
    make_user("Discord admin", role=ClubRole.ADMIN, discord_id=discord_id)
    response = bot_client.post(
        "/weeks/", json={"label": "Bot admin week"}, headers=as_discord(discord_id)
    )
    assert response.status_code == 201


def test_votes_private(client, make_user, week):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    nomination = _nominate(client, make_user("N", role=ClubRole.MEMBER), week)
    for voter in (u, v):
        assert (
            client.post(
                f"/weeks/{week['id']}/votes",
                json={"nomination_id": nomination["id"], "week_id": week["id"], "rank": 1},
                headers=as_user(voter),
            ).status_code
            == 201
        )

    votes = client.get("/votes", headers=as_user(u)).json()
    assert [vote["user_id"] for vote in votes] == [str(u.id)]

    v_vote = client.get("/votes", headers=as_user(v)).json()[0]
    assert client.get(f"/votes/{v_vote['id']}", headers=as_user(u)).status_code == 404
    assert client.get(f"/votes/{v_vote['id']}", headers=as_user(v)).status_code == 200


def test_listing_another_members_votes_is_refused(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    assert client.get(f"/votes?user_id={v.id}", headers=as_user(u)).status_code == 403


def test_no_client_reads_ballots_as_itself(bot_client):
    assert bot_client.get("/votes").status_code == 403
