"""Spec: listening/rediscovery, coverage and activity decide whether anything is forgotten."""

from datetime import UTC, datetime, timedelta

import pytest

from sidetrack.catalog import Track
from sidetrack.identity import User
from sidetrack.listening import ImportCoverage, ListenEvent, ListenSource, sessionize
from sidetrack.listening.rediscovery import forgotten_favourites

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 1, 15, tzinfo=UTC)
MARCH_2021 = datetime(2021, 3, 1, 12, tzinfo=UTC)


def _user(db):
    user = User(display_name="Listener", timezone="UTC")
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


def _cover(db, user, start, end):
    db.add(
        ImportCoverage(
            user_id=user.id,
            provider="listenbrainz",
            account="synthetic",
            earliest_played_at=start,
            latest_played_at=end,
        )
    )


def _old_favourite(db, user, plays=10):
    song = _track(db, "Old Song")
    for day in range(plays):
        _play(db, user, song, MARCH_2021 + timedelta(days=day))
    return song


def _recent_activity(db, user, days=25, per_day=3):
    filler = _track(db, "Recent Song")
    for day in range(1, days + 1):
        for index in range(per_day):
            _play(db, user, filler, NOW - timedelta(days=day, minutes=10 * index))


def _forgotten(db, user):
    db.flush()
    sessionize(db, user.id)
    return forgotten_favourites(db, user.id, now=NOW)


def test_no_import_is_not_imported_even_with_listens(db):
    user = _user(db)
    _old_favourite(db, user)
    _recent_activity(db, user)
    result = _forgotten(db, user)
    assert result["state"] == "not_imported"
    assert result["tracks"] == []
    assert result["coverage_start"] is None
    assert result["rules"]["forgotten_days"] == 365


def test_coverage_ending_early_is_a_gap_naming_the_end(db):
    user = _user(db)
    _old_favourite(db, user)
    _cover(db, user, MARCH_2021, NOW - timedelta(days=200))
    result = _forgotten(db, user)
    assert result["state"] == "coverage_gap"
    assert result["coverage_end"] == NOW - timedelta(days=200)
    assert result["tracks"] == []


def test_coverage_starting_inside_the_window_is_a_gap(db):
    user = _user(db)
    _cover(db, user, NOW - timedelta(days=100), NOW)
    assert _forgotten(db, user)["state"] == "coverage_gap"


def test_covered_with_zero_listens_is_not_not_imported(db):
    user = _user(db)
    _cover(db, user, MARCH_2021, NOW)
    result = _forgotten(db, user)
    assert result["state"] == "insufficient_history"
    assert (result["recent_plays"], result["recent_days"]) == (0, 0)


def test_quiet_recent_year_is_insufficient_history_with_counts(db):
    user = _user(db)
    _old_favourite(db, user)
    _recent_activity(db, user, days=12, per_day=3)
    _recent_activity(db, user, days=0)
    _cover(db, user, MARCH_2021, NOW)
    result = _forgotten(db, user)
    assert result["state"] == "insufficient_history"
    assert (result["recent_plays"], result["recent_days"]) == (36, 12)
    assert result["tracks"] == []


def test_many_plays_on_few_days_is_insufficient(db):
    user = _user(db)
    _recent_activity(db, user, days=10, per_day=8)
    _cover(db, user, MARCH_2021, NOW)
    result = _forgotten(db, user)
    assert result["state"] == "insufficient_history"
    assert (result["recent_plays"], result["recent_days"]) == (80, 10)


def test_checks_pass_but_nothing_qualifies(db):
    user = _user(db)
    _old_favourite(db, user, plays=3)
    _recent_activity(db, user)
    _cover(db, user, MARCH_2021, NOW - timedelta(days=1))
    result = _forgotten(db, user)
    assert result["state"] == "none_found"
    assert result["tracks"] == []
    assert result["coverage_start"] == MARCH_2021
    assert (result["recent_plays"], result["recent_days"]) == (75, 25)


def test_a_forgotten_favourite_is_found_with_its_details(db):
    user = _user(db)
    song = _old_favourite(db, user)
    _recent_activity(db, user)
    _cover(db, user, MARCH_2021, NOW - timedelta(days=1))
    result = _forgotten(db, user)
    assert result["state"] == "found"
    [row] = result["tracks"]
    assert row["track_id"] == song.id
    assert (row["title"], row["artist_name"]) == ("Old Song", "Artist")
    assert row["peak_plays"] == row["total_plays"] == 10
    assert row["last_played_at"] == MARCH_2021 + timedelta(days=9)
    assert result["rules"]["rule_version"] == "forgotten-v1"


def test_a_recent_play_keeps_the_track_off_the_list(db):
    user = _user(db)
    song = _old_favourite(db, user)
    _play(db, user, song, NOW - timedelta(days=200))
    _recent_activity(db, user)
    _cover(db, user, MARCH_2021, NOW - timedelta(days=1))
    assert _forgotten(db, user)["state"] == "none_found"


def test_another_users_history_is_not_read(db):
    user, other = _user(db), _user(db)
    _old_favourite(db, other)
    _recent_activity(db, other)
    _cover(db, other, MARCH_2021, NOW)
    assert _forgotten(db, user)["state"] == "not_imported"
