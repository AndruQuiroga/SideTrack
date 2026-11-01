"""Spec: analysis/listen-audio-resolution: YouTube IDs on a track's listens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from test_track_audio_links import make_track

from sidetrack.identity import User
from sidetrack.listening import ListenEvent, ListenSource, track_video_ids

pytestmark = pytest.mark.unit

START = datetime(2026, 6, 1, tzinfo=UTC)


def play(db, user, track, minutes, metadata):
    db.add(
        ListenEvent(
            user_id=user.id,
            track_id=track.id,
            played_at=START + timedelta(minutes=minutes),
            source=ListenSource.LISTENBRAINZ,
            metadata_=metadata,
        )
    )
    db.flush()


def lb(youtube_id):
    return {"listenbrainz": {"youtube_id": youtube_id, "recording_mbid": None}}


@pytest.fixture
def listener(db):
    user = User(display_name="Listener")
    db.add(user)
    db.flush()
    return user


def test_returns_distinct_pairs_and_skips_listens_without_a_video(db, listener):
    uploaded = make_track(db)
    plain = make_track(db, title="Plain")
    lastfm = make_track(db, "A", "B")
    play(db, listener, uploaded, 0, lb("abc123"))
    play(db, listener, uploaded, 10, lb("abc123"))
    play(db, listener, uploaded, 20, lb("xyz789"))
    play(db, listener, plain, 30, lb(None))
    play(db, listener, lastfm, 40, {"lastfm": {"mbid": "m"}})
    play(db, listener, lastfm, 50, None)

    pairs = track_video_ids(db)

    assert sorted(pairs) == sorted([(uploaded.id, "abc123"), (uploaded.id, "xyz789")])


def test_can_be_limited_to_one_user(db, listener):
    other = User(display_name="Other")
    db.add(other)
    db.flush()
    track = make_track(db)
    play(db, listener, track, 0, lb("mine"))
    play(db, other, track, 5, lb("theirs"))

    assert track_video_ids(db, listener.id) == [(track.id, "mine")]
