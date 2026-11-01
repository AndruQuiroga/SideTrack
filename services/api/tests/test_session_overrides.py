"""Spec: listening/listen-sessions, the owner-only review routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.catalog import Album, Track
from sidetrack.listening import ListenEvent, ListenSource, list_sessions, sessionize
from sidetrack.types import ClubRole, ListeningVisibility

from .conftest import as_user

pytestmark = pytest.mark.unit


@pytest.fixture()
def session(db, member):
    album = Album(title="Record", artist_name="Artist")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Artist")
    db.add(track)
    db.flush()
    member.timezone = "UTC"
    start = datetime(2026, 6, 1, 23, tzinfo=UTC)
    for index in range(20):
        db.add(
            ListenEvent(
                user_id=member.id,
                track_id=track.id,
                played_at=start + timedelta(minutes=10 * index),
                source=ListenSource.MANUAL,
            )
        )
    db.flush()
    sessionize(db, member.id)
    return list_sessions(db, member.id)[0][0]


def test_owner_lists_sessions_with_their_flags(client, member, session):
    response = client.get(f"/users/{member.id}/listening/sessions", headers=as_user(member))
    assert response.status_code == 200
    body = response.json()[0]
    assert body["id"] == str(session.id)
    assert body["kind"] == body["effective_kind"] == "night_autoplay"
    assert body["override"] is None
    assert body["rule_version"] == "night-v1"


def test_owner_sets_and_clears_an_override(client, member, session):
    path = f"/users/{member.id}/listening/sessions/{session.id}/override"
    kept = client.put(path, json={"override": "keep"}, headers=as_user(member))
    assert kept.status_code == 200
    assert (kept.json()["kind"], kept.json()["effective_kind"]) == ("night_autoplay", "keep")
    cleared = client.delete(path, headers=as_user(member))
    assert cleared.status_code == 200
    assert cleared.json()["effective_kind"] == "night_autoplay"


def test_unknown_override_is_refused(client, member, session):
    path = f"/users/{member.id}/listening/sessions/{session.id}/override"
    response = client.put(path, json={"override": "maybe"}, headers=as_user(member))
    assert response.status_code == 422


def test_sessions_are_hidden_from_other_members_even_when_shared(
    client, db, member, make_user, session
):
    member.listening_visibility = ListeningVisibility.CLUB
    db.flush()
    other = make_user("Other", role=ClubRole.MEMBER)
    listing = client.get(f"/users/{member.id}/listening/sessions", headers=as_user(other))
    assert listing.status_code == 404
    path = f"/users/{member.id}/listening/sessions/{session.id}/override"
    assert client.put(path, json={"override": "keep"}, headers=as_user(other)).status_code == 404
    assert client.delete(path, headers=as_user(other)).status_code == 404


def test_another_users_session_is_not_found_under_your_own_path(client, make_user, session):
    other = make_user("Other", role=ClubRole.MEMBER)
    path = f"/users/{other.id}/listening/sessions/{session.id}/override"
    assert client.put(path, json={"override": "keep"}, headers=as_user(other)).status_code == 404
