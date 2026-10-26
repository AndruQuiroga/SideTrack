"""Listening delegates catalog writes through the public catalog operation."""

import importlib
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from sidetrack.catalog import Album, Track, resolve_listen_track
from sidetrack.identity import User
from sidetrack.listening import ListenEvent, ingest_lastfm
from sidetrack.types import ListenSource

pytestmark = pytest.mark.integration


def test_ingest_uses_catalog_operation_and_persists_listen(db, monkeypatch):
    ingest = importlib.import_module("sidetrack.listening.ingest")
    metadata = importlib.import_module("sidetrack.catalog.metadata")
    user = User(display_name="Listener")
    album = Album(title="Record", artist_name="Artist")
    db.add_all([user, album])
    db.flush()
    monkeypatch.setattr(metadata, "upsert_album_from_release_group", lambda *a, **kw: album)
    monkeypatch.setattr(
        ingest.lastfm,
        "get_recent_tracks",
        lambda *a, **kw: {
            "track": [
                {
                    "name": "Song",
                    "artist": {"#text": "Artist"},
                    "album": {"#text": "Record"},
                    "mbid": "recording-id",
                    "date": {"uts": "1792886400"},
                }
            ],
        },
    )
    calls = []

    def catalog_operation(*args, **kwargs):
        track = resolve_listen_track(*args, **kwargs)
        calls.append(track.id)
        return track

    monkeypatch.setattr(ingest, "resolve_listen_track", catalog_operation)
    result = ingest_lastfm(db, user_id=user.id, lastfm_username="listener")

    assert result == {"inserted": 1, "last_ts": 1792886400}
    track = db.scalar(select(Track).where(Track.musicbrainz_id == "recording-id"))
    listen = db.scalar(select(ListenEvent).where(ListenEvent.user_id == user.id))
    assert calls == [track.id]
    assert track.album_id == album.id
    assert listen.track_id == track.id
    assert listen.source is ListenSource.LASTFM
    assert listen.played_at == datetime.fromtimestamp(1792886400, tz=UTC)


def test_unresolvable_scrobble_remains_unavailable(db, monkeypatch):
    metadata = importlib.import_module("sidetrack.catalog.metadata")
    monkeypatch.setattr(metadata, "resolve_recording_mbid", lambda *a, **kw: None)
    assert (
        resolve_listen_track(
            db,
            track_name="Song",
            artist_name="Artist",
            album_name=None,
            track_mbid=None,
        )
        is None
    )
