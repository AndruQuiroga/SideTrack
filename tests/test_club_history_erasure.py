"""Erasure keeps other participants' history and prevents same-source resurrection."""

from datetime import UTC, date, datetime

from sqlalchemy import select

from sidetrack.club import (
    HistoryBatch,
    HistorySource,
    SinglesRating,
    SinglesSession,
    SinglesSong,
    SinglesSubmission,
)
from sidetrack.club.history.store import source_state, target_hash
from sidetrack.identity import User


def test_erased_author_keeps_other_ratings_and_source_is_not_new_again(db):
    owner, other = User(display_name="Submitter"), User(display_name="Other listener")
    event = SinglesSession(
        guild_id="1", source_thread_id="100", original_label="Session", event_date=date(2026, 1, 14)
    )
    run = HistoryBatch(
        guild_id="1", plan_digest="a" * 64, source_digest="b" * 64, parser_version=1, counts={}
    )
    db.add_all([owner, other, event, run])
    db.flush()
    song = SinglesSong(session_id=event.id, title="Song", artist_name="Band", position=100)
    db.add(song)
    db.flush()
    submission = SinglesSubmission(
        session_id=event.id, song_id=song.id, user_id=owner.id, submitted_at=datetime.now(UTC)
    )
    values = {
        "session_id": event.id,
        "song_id": song.id,
        "created_at": datetime.now(UTC),
        "phase": "first",
        "value": 4,
    }
    own_rating = SinglesRating(**values, user_id=owner.id, review="My review")
    other_rating = SinglesRating(**values, user_id=other.id)
    db.add_all([submission, own_rating, other_rating])
    db.flush()
    record = {
        "key": "singles_rating:1:100:101",
        "kind": "singles_rating",
        "evidence_hash": "e" * 64,
    }
    db.add(
        HistorySource(
            source_key=record["key"],
            batch_id=run.id,
            kind=record["kind"],
            thread_id="100",
            message_id="101",
            evidence_hash=record["evidence_hash"],
            target_kind="singles_rating",
            target_id=own_rating.id,
            target_hash=target_hash(own_rating),
        )
    )
    db.flush()
    assert source_state(db, record)["action"] == "reuse"
    db.delete(owner)
    db.flush()
    db.expire_all()
    assert db.scalars(select(SinglesSubmission)).all() == []
    assert db.scalars(select(SinglesRating)).all() == [other_rating]
    assert db.get(SinglesSong, song.id) is not None
    assert source_state(db, record)["action"] == "erased"
    assert "author_name" not in HistorySource.__table__.columns
