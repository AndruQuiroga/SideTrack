"""Spec: listening/rediscovery, included plays follow effective session classification."""

from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.catalog import Track
from sidetrack.identity import User
from sidetrack.listening import ListenEvent, ListenSource, list_sessions, sessionize, set_override
from sidetrack.listening.rediscovery import find_forgotten, included_plays

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 1, tzinfo=UTC)
FIRST_DAY = datetime(2021, 3, 1, 12, tzinfo=UTC)
NIGHT = datetime(2021, 3, 10, 23, tzinfo=UTC)


def _user(db, timezone):
    user = User(display_name="Listener", timezone=timezone)
    db.add(user)
    db.flush()
    return user


def _track(db, title):
    track = Track(title=title, artist_name="Artist")
    db.add(track)
    db.flush()
    return track


def _play(db, user, track, at):
    db.add(
        ListenEvent(user_id=user.id, track_id=track.id, played_at=at, source=ListenSource.MANUAL)
    )


def _history(db, user):
    """Six daytime plays and three inside one late-night session of 13 listens."""
    song, filler = _track(db, "Song"), _track(db, "Filler")
    for day in range(6):
        _play(db, user, song, FIRST_DAY + timedelta(days=day))
    for index in range(13):
        track = song if index < 3 else filler
        _play(db, user, track, NIGHT + timedelta(minutes=6 * index))
    db.flush()
    sessionize(db, user.id)
    return song


def _counts(found):
    return {row["track_id"]: row["peak_plays"] for row in found}


def test_night_autoplay_is_excluded_by_default_and_counted(db):
    user = _user(db, "UTC")
    song = _history(db, user)
    included = included_plays(db, user.id)
    assert included.excluded_autoplay == 13
    assert included.unknown_session == 0
    assert sum(1 for track_id, _ in included.plays if track_id == song.id) == 6
    assert find_forgotten(included.plays, NOW) == []


def test_keep_override_counts_the_session(db):
    user = _user(db, "UTC")
    song = _history(db, user)
    [night] = [s for s, _ in list_sessions(db, user.id) if s.kind == "night_autoplay"]
    set_override(db, night, "keep")
    included = included_plays(db, user.id)
    assert included.excluded_autoplay == 0
    assert _counts(find_forgotten(included.plays, NOW))[song.id] == 9


def test_autoplay_override_excludes_an_unflagged_session(db):
    user = _user(db, "UTC")
    _history(db, user)
    day = next(s for s, _ in list_sessions(db, user.id) if s.kind == "unclassified")
    set_override(db, day, "autoplay")
    assert included_plays(db, user.id).excluded_autoplay == 14


def test_include_autoplay_toggle_counts_everything(db):
    user = _user(db, "UTC")
    song = _history(db, user)
    included = included_plays(db, user.id, include_autoplay=True)
    assert included.excluded_autoplay == 0
    assert _counts(find_forgotten(included.plays, NOW))[song.id] == 9


def test_unknown_sessions_are_included_and_disclosed(db):
    user = _user(db, None)
    song = _history(db, user)
    included = included_plays(db, user.id)
    assert included.excluded_autoplay == 0
    assert included.unknown_session == 19
    assert _counts(find_forgotten(included.plays, NOW))[song.id] == 9


def test_plays_outside_any_session_are_counted_as_unknown(db):
    user = _user(db, "UTC")
    song = _track(db, "Song")
    _play(db, user, song, FIRST_DAY)
    db.flush()
    included = included_plays(db, user.id)
    assert (len(included.plays), included.unknown_session) == (1, 1)


def test_other_users_plays_are_not_read(db):
    user, other = _user(db, "UTC"), _user(db, "UTC")
    _history(db, other)
    assert included_plays(db, user.id).plays == []
