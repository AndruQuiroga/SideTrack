"""Independent sessions, neutral songs and phase-aware contribution constraints."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sidetrack.club import SinglesRating, SinglesSession, SinglesSong, SinglesSubmission, Week
from sidetrack.identity import User


def setup_session(db):
    event = SinglesSession(
        guild_id="1",
        source_thread_id="100",
        week_number=7,
        original_label="Week 7",
        event_date=date(2026, 1, 14),
    )
    user = User(display_name="Participant")
    db.add_all([event, user])
    db.flush()
    song = SinglesSong(session_id=event.id, title="Song", artist_name="Artist", position=101)
    db.add(song)
    db.flush()
    return event, song, user


def test_session_does_not_require_album_and_numbers_do_not_collide(db):
    event, song, _ = setup_session(db)
    album_week = Week(label="Album week 7", week_number=7)
    db.add(album_week)
    db.flush()
    assert event.id != album_week.id
    assert song.track_id is None
    assert event.event_at is None


def test_source_thread_cannot_be_imported_twice(db):
    setup_session(db)
    db.add(SinglesSession(guild_id="1", source_thread_id="100", original_label="Duplicate"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_first_and_final_are_distinct_but_duplicate_phase_is_rejected(db):
    event, song, user = setup_session(db)
    values = {
        "session_id": event.id,
        "song_id": song.id,
        "user_id": user.id,
        "created_at": datetime.now(UTC),
    }
    db.add_all(
        [
            SinglesRating(**values, phase="first", value=3.5),
            SinglesRating(**values, phase="final", value=4),
        ]
    )
    db.flush()
    assert len(db.scalars(select(SinglesRating)).all()) == 2
    db.add(SinglesRating(**values, phase="final", value=5))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_cross_session_song_reference_is_rejected(db):
    event, song, user = setup_session(db)
    other = SinglesSession(guild_id="1", source_thread_id="200", original_label="Other")
    db.add(other)
    db.flush()
    db.add(
        SinglesSubmission(
            session_id=other.id, song_id=song.id, user_id=user.id, submitted_at=datetime.now(UTC)
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("phase,value", [("unknown", 3), ("first", 0), ("final", 6)])
def test_invalid_phase_and_score_are_rejected_by_database(db, phase, value):
    event, song, user = setup_session(db)
    db.add(
        SinglesRating(
            session_id=event.id,
            song_id=song.id,
            user_id=user.id,
            phase=phase,
            value=value,
            created_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
