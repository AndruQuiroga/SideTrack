"""Spec: identity/personal-data-visibility."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sidetrack.catalog import Album, Track
from sidetrack.identity import User
from sidetrack.listening import ListenEvent
from sidetrack.types import ClubRole, ListeningVisibility, ListenSource

from .conftest import as_discord, as_user, snowflake

pytestmark = pytest.mark.unit


@pytest.fixture()
def track(db):
    album = Album(title="Personal LP", artist_name="Band")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Band")
    db.add(track)
    db.flush()
    return track


def _listen(db, user, track):
    event = ListenEvent(
        user_id=user.id,
        track_id=track.id,
        played_at=datetime(2026, 10, 1, tzinfo=UTC),
        source=ListenSource.MANUAL,
        ingested_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def _share(db, user):
    user.listening_visibility = ListeningVisibility.CLUB
    db.flush()


def test_new_users_are_private(client, db):
    created = client.post("/users/", json={"display_name": "New"}).json()
    assert created["listening_visibility"] == "private"
    assert db.get(User, created["id"]).listening_visibility is ListeningVisibility.PRIVATE


def test_owner_changes_visibility(client, member):
    response = client.patch(
        f"/users/{member.id}", json={"listening_visibility": "club"}, headers=as_user(member)
    )
    assert response.status_code == 200
    assert response.json()["listening_visibility"] == "club"


def test_cannot_change_someone_elses_setting(client, make_user, db):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    response = client.patch(
        f"/users/{v.id}", json={"listening_visibility": "club"}, headers=as_user(u)
    )
    assert response.status_code == 403
    db.expire_all()
    assert db.get(User, v.id).listening_visibility is ListeningVisibility.PRIVATE


def test_other_member_cannot_read_linked_accounts(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    assert client.get(f"/users/{v.id}/linked-accounts", headers=as_user(u)).status_code == 404


def test_linked_accounts_stay_private_when_shared(client, make_user, db):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    _share(db, v)
    assert client.get(f"/users/{v.id}/linked-accounts", headers=as_user(u)).status_code == 404


def test_provider_lookup_needs_provisioning_scope(client, member):
    response = client.get(
        f"/users/lookup/by-provider/discord/{snowflake()}", headers=as_user(member)
    )
    assert response.status_code == 403


def test_provisioning_attaches_first_discord_account_only(client, bot_client, member):
    first = bot_client.post(
        f"/users/{member.id}/linked-accounts",
        json={"provider": "discord", "provider_user_id": snowflake()},
    )
    assert first.status_code == 201
    second = bot_client.post(
        f"/users/{member.id}/linked-accounts",
        json={"provider": "discord", "provider_user_id": snowflake()},
    )
    assert second.status_code == 403
    lastfm = client.post(
        f"/users/{member.id}/linked-accounts",
        json={"provider": "lastfm", "provider_user_id": "someone"},
    )
    assert lastfm.status_code == 403


def test_private_listening(client, make_user, db, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    _listen(db, v, track)
    response = client.get(f"/users/{v.id}/listening/recent", headers=as_user(u))
    assert response.status_code == 404


def test_shared_with_the_club(client, make_user, db, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    _listen(db, v, track)
    _share(db, v)
    response = client.get(f"/users/{v.id}/listening/recent", headers=as_user(u))
    assert response.status_code == 200
    assert [item["track_name"] for item in response.json()] == ["Song"]


def test_shared_listening_hidden_from_non_members(client, make_user, db, track):
    outsider = make_user("Outsider")
    v = make_user("V", role=ClubRole.MEMBER)
    _share(db, v)
    assert client.get(f"/users/{v.id}/listening/recent", headers=as_user(outsider)).status_code == (
        404
    )


def test_unfiltered_listen_event_list_is_own(client, make_user, db, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    own = _listen(db, u, track)
    _listen(db, v, track)
    _share(db, v)
    response = client.get("/listen-events/", headers=as_user(u))
    assert response.status_code == 200
    assert [e["id"] for e in response.json()] == [str(own.id)]


def test_listen_event_list_for_private_user_is_404(client, make_user, db, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    _listen(db, v, track)
    assert client.get(f"/listen-events/?user_id={v.id}", headers=as_user(u)).status_code == 404


def test_listen_event_by_id_follows_visibility(client, make_user, db, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    event = _listen(db, v, track)
    assert client.get(f"/listen-events/{event.id}", headers=as_user(u)).status_code == 404


def test_taste_profiles_follow_visibility(client, make_user, db):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    path = f"/users/{v.id}/taste-profiles/"
    assert client.get(path, headers=as_user(u)).status_code == 404
    _share(db, v)
    assert client.get(path, headers=as_user(u)).status_code == 200


def test_listen_import_for_another_user(client, make_user, track):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    response = client.post(
        "/listen-events/",
        json={
            "listens": [
                {
                    "user_id": str(v.id),
                    "track_id": str(track.id),
                    "played_at": "2026-10-01T00:00:00Z",
                    "source": "manual",
                }
            ]
        },
        headers=as_user(u),
    )
    assert response.status_code == 403


def test_ingest_for_another_user(client, make_user, db):
    from sidetrack.queue_models import BackgroundJob

    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    response = client.post(
        "/ingest/lastfm",
        json={"user_id": str(v.id), "lastfm_username": "v"},
        headers=as_user(u),
    )
    assert response.status_code == 403
    assert db.query(BackgroundJob).count() == 0


def test_recompute_for_another_user(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    response = client.post(f"/users/{v.id}/taste-profiles/recompute", headers=as_user(u))
    assert response.status_code == 403


def test_bot_never_reads_listening(bot_client, make_user, db):
    discord_id = snowflake()
    user = make_user("Bot user", role=ClubRole.MEMBER, discord_id=discord_id)
    response = bot_client.get(f"/users/{user.id}/listening/recent", headers=as_discord(discord_id))
    assert response.status_code == 403


def test_someone_elses_recommendations(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    assert client.get(f"/recommendations?user_id={v.id}", headers=as_user(u)).status_code == 404
    assert client.get("/recommendations", headers=as_user(u)).status_code == 200


def test_compatibility_other_user_private(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    assert client.get(f"/users/{u.id}/compatibility/{v.id}", headers=as_user(u)).status_code == 404


def test_compatibility_with_consent(client, make_user, db):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    _share(db, v)
    response = client.get(f"/users/{u.id}/compatibility/{v.id}", headers=as_user(u))
    assert response.status_code == 200
    assert "score" in response.json()


def test_compatibility_third_party(client, make_user, db):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    w = make_user("W", role=ClubRole.MEMBER)
    _share(db, u)
    _share(db, v)
    assert client.get(f"/users/{u.id}/compatibility/{v.id}", headers=as_user(w)).status_code == 404


def test_member_profile_visibility(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    outsider = make_user("Outsider")
    assert client.get(f"/users/{v.id}", headers=as_user(u)).status_code == 200
    assert client.get(f"/users/{v.id}", headers=as_user(outsider)).status_code == 404
    assert client.get(f"/users/{outsider.id}", headers=as_user(outsider)).status_code == 200


def test_follow_only_as_self(client, make_user):
    u = make_user("U", role=ClubRole.MEMBER)
    v = make_user("V", role=ClubRole.MEMBER)
    assert client.post(f"/users/{v.id}/follow/{u.id}", headers=as_user(u)).status_code == 404
    assert client.post(f"/users/{u.id}/follow/{v.id}", headers=as_user(u)).status_code == 201


def test_search_finds_people_only_for_members(client, make_user):
    make_user("Findable", role=ClubRole.MEMBER)
    outsider = make_user("Outsider")
    member = make_user("Searcher", role=ClubRole.MEMBER)
    assert client.get("/search?q=Findable", headers=as_user(outsider)).json()["users"] == []
    names = [
        u["display_name"]
        for u in client.get("/search?q=Find", headers=as_user(member)).json()["users"]
    ]
    assert names == ["Findable"]
