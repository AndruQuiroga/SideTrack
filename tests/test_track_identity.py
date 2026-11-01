"""Spec: listening/listenbrainz-import, plays without a release and no MusicBrainz calls."""

import pytest
from sqlalchemy import func, select

from sidetrack.catalog import Album, Track, resolve_track_identity
from sidetrack.external import http

pytestmark = pytest.mark.unit

MBID = "00000000-0000-4000-8000-000000000021"


@pytest.fixture(autouse=True)
def no_provider_requests(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("resolve_track_identity made an HTTP request")

    monkeypatch.setattr(http, "request_json", refuse)
    monkeypatch.setattr(http, "_get_client", refuse)


def test_mapped_listen_uses_the_recording_mbid(db):
    first = resolve_track_identity(db, artist="Band", title="Song", recording_mbid=MBID)
    again = resolve_track_identity(db, artist="Renamed", title="Other", recording_mbid=MBID)
    assert again.id == first.id
    assert first.musicbrainz_id == MBID


def test_unresolved_with_release_creates_a_bare_album(db):
    track = resolve_track_identity(db, artist="Band", title="Song", release="Record")
    album = db.get(Album, track.album_id)
    assert (album.title, album.artist_name, album.musicbrainz_id) == ("Record", "Band", None)


def test_existing_album_is_reused_case_insensitively(db):
    album = Album(title="Record", artist_name="Band")
    db.add(album)
    db.flush()
    track = resolve_track_identity(db, artist="BAND", title="Song", release="RECORD")
    assert track.album_id == album.id


def test_unresolved_without_release_has_no_album(db):
    track = resolve_track_identity(db, artist="Band", title="Upload")
    assert track.album_id is None
    assert track.album is None
    assert db.scalar(select(func.count()).select_from(Album)) == 0


def test_same_track_twice_is_one_track(db):
    first = resolve_track_identity(db, artist="Band", title="Upload")
    second = resolve_track_identity(db, artist="band", title="UPLOAD")
    assert second.id == first.id


def test_same_names_on_another_release_are_another_track(db):
    first = resolve_track_identity(db, artist="Band", title="Song", release="One")
    second = resolve_track_identity(db, artist="Band", title="Song", release="Two")
    assert second.id != first.id


def test_a_mapping_fills_in_a_track_found_by_name(db):
    first = resolve_track_identity(db, artist="Band", title="Upload")
    second = resolve_track_identity(db, artist="Band", title="Upload", recording_mbid=MBID)
    assert second.id == first.id
    assert first.musicbrainz_id == MBID


def test_names_too_long_for_the_catalog_are_cut_not_refused(db):
    track = resolve_track_identity(db, artist="Band", title="x" * 300)
    assert len(track.title) == 255
    assert isinstance(track, Track)


def test_blank_names_are_refused(db):
    with pytest.raises(ValueError):
        resolve_track_identity(db, artist=" ", title="Song")
