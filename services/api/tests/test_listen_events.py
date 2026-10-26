"""Spec: listening/listen-events, responses return stored rows."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sidetrack.catalog import Album, Track
from sidetrack.listening import ListenEvent
from sidetrack.types import ClubRole, ListeningVisibility, ListenSource

from .conftest import as_user

pytestmark = pytest.mark.unit


@pytest.fixture()
def track(db):
    album = Album(title="Listen LP", artist_name="Band")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Band")
    db.add(track)
    db.flush()
    return track


def _listen(db, user, track, day, metadata=None):
    event = ListenEvent(
        user_id=user.id,
        track_id=track.id,
        played_at=datetime(2026, 10, day, tzinfo=UTC),
        source=ListenSource.MANUAL,
        ingested_at=datetime.now(UTC),
        metadata_=metadata,
    )
    db.add(event)
    db.flush()
    return event


def test_recording_a_listen_with_metadata(client, member, track):
    response = client.post(
        "/listen-events/",
        json={
            "listens": [
                {
                    "track_id": str(track.id),
                    "played_at": "2026-10-01T00:00:00Z",
                    "source": "manual",
                    "metadata": {"device": "turntable"},
                }
            ]
        },
        headers=as_user(member),
    )

    assert response.status_code == 201
    [listen] = response.json()
    assert listen["metadata"] == {"device": "turntable"}
    assert listen["user_id"] == str(member.id)


def test_listing_own_listens(client, member, track, db):
    older = _listen(db, member, track, 1, {"device": "phone"})
    newer = _listen(db, member, track, 2, {"device": "turntable"})

    response = client.get("/listen-events/", headers=as_user(member))

    assert response.status_code == 200
    body = response.json()
    assert [e["id"] for e in body] == [str(newer.id), str(older.id)]
    assert [e["metadata"] for e in body] == [{"device": "turntable"}, {"device": "phone"}]


def test_reading_one_listen(client, member, track, db):
    event = _listen(db, member, track, 1)

    response = client.get(f"/listen-events/{event.id}", headers=as_user(member))

    assert response.status_code == 200
    assert response.json()["id"] == str(event.id)
    assert response.json()["metadata"] is None


def test_reading_a_shared_users_listens(client, make_user, member, track, db):
    sharer = make_user("Sharer", role=ClubRole.MEMBER)
    sharer.listening_visibility = ListeningVisibility.CLUB
    event = _listen(db, sharer, track, 1)

    response = client.get(f"/listen-events/?user_id={sharer.id}", headers=as_user(member))

    assert response.status_code == 200
    assert [e["id"] for e in response.json()] == [str(event.id)]
