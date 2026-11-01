"""Spec: listening/listen-sessions."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select

from sidetrack.catalog import Album, Track
from sidetrack.identity import User, add_timezone_period
from sidetrack.listening import (
    ListenEvent,
    ListenSession,
    ListenSessionOverride,
    ListenSource,
    effective_kind,
    list_sessions,
    sessionize,
    set_override,
)

pytestmark = pytest.mark.unit

PHOENIX = "America/Phoenix"  # UTC-7 all year
DAY = datetime(2026, 6, 1, tzinfo=UTC)


@pytest.fixture
def track(db):
    album = Album(title="Record", artist_name="Artist")
    db.add(album)
    db.flush()
    track = Track(album_id=album.id, title="Song", artist_name="Artist")
    db.add(track)
    db.flush()
    return track


@pytest.fixture
def listener(db):
    user = User(display_name="Listener", timezone="UTC")
    db.add(user)
    db.flush()
    return user


def _play(db, user, *times):
    for at in times:
        db.add(
            ListenEvent(
                user_id=user.id,
                track_id=_track_id(db),
                played_at=at,
                source=ListenSource.MANUAL,
            )
        )
    db.flush()


def _track_id(db):
    return db.scalar(select(Track.id))


def _at(hours, minutes=0):
    return DAY + timedelta(hours=hours, minutes=minutes)


def _spread(start, end, count):
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def _sessions(db, user):
    return db.scalars(
        select(ListenSession)
        .where(ListenSession.user_id == user.id)
        .order_by(ListenSession.started_at)
    ).all()


def test_gap_splits_sessions(db, track, listener):
    _play(db, listener, _at(20), _at(20, 4), _at(20, 40), _at(21, 30))
    sessionize(db, listener.id)
    assert [session.listen_count for session in _sessions(db, listener)] == [2, 1, 1]


def test_exactly_thirty_minutes_stays_in_the_session(db, track, listener):
    _play(db, listener, _at(20), _at(20, 30))
    sessionize(db, listener.id)
    assert len(_sessions(db, listener)) == 1


def test_every_listen_belongs_to_one_session(db, track, listener):
    _play(db, listener, _at(20), _at(20, 4), _at(22))
    sessionize(db, listener.id)
    assert (
        db.scalar(
            select(func.count()).select_from(ListenEvent).where(ListenEvent.session_id.is_(None))
        )
        == 0
    )


def test_new_listens_extend_the_last_session(db, track, listener):
    _play(db, listener, _at(20), _at(20, 4))
    sessionize(db, listener.id)
    _play(db, listener, _at(20, 14))
    sessionize(db, listener.id, since=_at(20, 14), until=_at(20, 14))
    sessions = _sessions(db, listener)
    assert len(sessions) == 1
    assert (sessions[0].listen_count, sessions[0].ended_at) == (3, _at(20, 14))


def test_older_listens_join_the_following_session(db, track, listener):
    _play(db, listener, _at(20, 10))
    sessionize(db, listener.id)
    _play(db, listener, _at(20))
    sessionize(db, listener.id, since=_at(20), until=_at(20))
    sessions = _sessions(db, listener)
    assert [(s.started_at, s.listen_count) for s in sessions] == [(_at(20), 2)]


def test_a_listen_between_two_sessions_joins_them(db, track, listener):
    _play(db, listener, _at(20), _at(21))
    sessionize(db, listener.id)
    assert len(_sessions(db, listener)) == 2
    _play(db, listener, _at(20, 30))
    sessionize(db, listener.id, since=_at(20, 30), until=_at(20, 30))
    assert [s.listen_count for s in _sessions(db, listener)] == [3]


def test_a_ranged_rebuild_leaves_distant_sessions_alone(db, track, listener):
    _play(db, listener, _at(1), _at(20))
    sessionize(db, listener.id)
    distant = _sessions(db, listener)[0]
    _play(db, listener, _at(20, 5))
    sessionize(db, listener.id, since=_at(20, 5), until=_at(20, 5))
    assert _sessions(db, listener)[0].id == distant.id


def test_sleep_tab_session_is_flagged(db, track, listener):
    _play(db, listener, *_spread(_at(23, 10), _at(26, 40), 40))
    sessionize(db, listener.id)
    session = _sessions(db, listener)[0]
    assert session.kind == "night_autoplay"
    assert session.rule_version == "night-v1"


def test_short_late_session_is_unclassified(db, track, listener):
    _play(db, listener, *_spread(_at(23, 10), _at(23, 35), 6))
    sessionize(db, listener.id)
    assert _sessions(db, listener)[0].kind == "unclassified"


def test_long_evening_session_is_unclassified(db, track, listener):
    _play(db, listener, *_spread(_at(20, 30), _at(26), 60))
    sessionize(db, listener.id)
    assert _sessions(db, listener)[0].kind == "unclassified"


def test_night_is_read_in_the_users_zone(db, track, listener):
    listener.timezone = PHOENIX
    db.flush()
    # 06:00 UTC is 23:00 in Phoenix.
    _play(db, listener, *_spread(_at(6), _at(9), 20))
    sessionize(db, listener.id)
    assert _sessions(db, listener)[0].kind == "night_autoplay"


def test_timezone_missing_then_set(db, track, listener):
    listener.timezone = None
    db.flush()
    _play(db, listener, *_spread(_at(23), _at(26), 20), _at(12))
    result = sessionize(db, listener.id)
    assert result["notes"] == ["timezone_missing"]
    assert {session.kind for session in _sessions(db, listener)} == {"unknown"}

    listener.timezone = "UTC"
    db.flush()
    result = sessionize(db, listener.id)
    assert result["notes"] == []
    assert {session.kind for session in _sessions(db, listener)} == {
        "night_autoplay",
        "unclassified",
    }


def test_rebuild_is_stable(db, track, listener):
    _play(db, listener, _at(20), _at(20, 4), *_spread(_at(23), _at(26), 20))
    sessionize(db, listener.id)
    first = [(s.started_at, s.ended_at, s.listen_count, s.kind) for s in _sessions(db, listener)]
    sessionize(db, listener.id)
    assert first == [
        (s.started_at, s.ended_at, s.listen_count, s.kind) for s in _sessions(db, listener)
    ]


def test_user_deleted(db, track, listener):
    _play(db, listener, _at(20))
    sessionize(db, listener.id)
    session = _sessions(db, listener)[0]
    set_override(db, session, "keep")
    user_id = listener.id
    db.execute(delete(User).where(User.id == user_id))
    assert db.scalar(select(func.count()).select_from(ListenSession)) == 0
    assert db.scalar(select(func.count()).select_from(ListenSessionOverride)) == 0


def test_keep_a_flagged_session(db, track, listener):
    _play(db, listener, *_spread(_at(23), _at(26), 20))
    sessionize(db, listener.id)
    session = _sessions(db, listener)[0]
    set_override(db, session, "keep")
    ((read, override),) = list_sessions(db, listener.id)
    assert read.kind == "night_autoplay"
    assert effective_kind(read, override) == "keep"


def test_clear_an_override(db, track, listener):
    _play(db, listener, *_spread(_at(23), _at(26), 20))
    sessionize(db, listener.id)
    session = _sessions(db, listener)[0]
    set_override(db, session, "keep")
    set_override(db, session, None)
    ((read, override),) = list_sessions(db, listener.id)
    assert override is None
    assert effective_kind(read, override) == "night_autoplay"


def test_override_survives_a_rebuild_with_the_same_boundaries(db, track, listener):
    _play(db, listener, *_spread(_at(23), _at(26), 20))
    sessionize(db, listener.id)
    set_override(db, _sessions(db, listener)[0], "keep")
    result = sessionize(db, listener.id)
    assert result["override_orphaned"] == 0
    assert effective_kind(*list_sessions(db, listener.id)[0]) == "keep"


def test_rebuild_changes_boundaries(db, track, listener):
    _play(db, listener, _at(20), _at(20, 5))
    sessionize(db, listener.id)
    set_override(db, _sessions(db, listener)[0], "autoplay")
    _play(db, listener, _at(20, 10))
    result = sessionize(db, listener.id)
    assert result["override_orphaned"] == 1
    read, override = list_sessions(db, listener.id)[0]
    assert override is None
    assert effective_kind(read, override) == "unclassified"


def test_night_uses_zone_at_session_start(db, track, listener):
    listener.timezone = "UTC"
    add_timezone_period(db, listener.id, _at(100), PHOENIX)
    # 06:00-09:00 UTC is 23:00-02:00 in Phoenix, but daytime in UTC.
    before = _spread(_at(6), _at(9), 20)
    after = _spread(_at(126), _at(129), 20)
    _play(db, listener, *before, *after)
    sessionize(db, listener.id)
    kinds = [session.kind for session in _sessions(db, listener)]
    assert kinds == ["unclassified", "night_autoplay"]


def test_same_clock_time_differs_across_a_move(db, track, listener):
    listener.timezone = "America/New_York"
    add_timezone_period(db, listener.id, _at(48), PHOENIX)
    # 03:00 UTC is 23:00 in New York (UTC-4 in June) and 20:00 in Phoenix (UTC-7).
    _play(db, listener, *_spread(_at(3), _at(6), 20), *_spread(_at(51), _at(54), 20))
    sessionize(db, listener.id)
    kinds = [session.kind for session in _sessions(db, listener)]
    assert kinds == ["night_autoplay", "unclassified"]


def test_rebuild_keeps_boundaries_and_overrides(db, track, listener):
    _play(db, listener, *_spread(_at(23), _at(26), 20))
    sessionize(db, listener.id)
    before = [(s.started_at, s.ended_at, s.listen_count) for s in _sessions(db, listener)]
    set_override(db, _sessions(db, listener)[0], "keep")
    add_timezone_period(db, listener.id, _at(0), PHOENIX)
    result = sessionize(db, listener.id)
    assert result["override_orphaned"] == 0
    assert [(s.started_at, s.ended_at, s.listen_count) for s in _sessions(db, listener)] == before
    assert _sessions(db, listener)[0].kind == "unclassified"
    assert effective_kind(*list_sessions(db, listener.id)[0]) == "keep"
