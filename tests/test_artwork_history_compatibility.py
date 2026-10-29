"""Artwork must not change legacy history meaning, hashes or erasure suppression."""

from artwork_support import ready_plan
from history_support import sample_plan
from sqlalchemy import func, select

from sidetrack.artwork_recovery import apply, check
from sidetrack.club import Notification, SinglesSong, SinglesSongArtwork
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan
from sidetrack.club.history.store import target_hash
from sidetrack.club.history.verification import verify_checked
from sidetrack.queue_models import BackgroundJob, JobSchedule


def test_artwork_preserves_history_verify_retry_and_side_effects(db):
    plan = sample_plan()
    history = check_plan(db, plan)
    apply_checked(db, history, expected_digest=history["digest"], source_plan=plan)
    song = db.scalar(select(SinglesSong))
    before = target_hash(song)
    counts = {
        m: db.scalar(select(func.count()).select_from(m))
        for m in (Notification, JobSchedule, BackgroundJob)
    }
    checked = check(db, ready_plan(db))
    apply(db, checked, checked["digest"])
    assert target_hash(song) == before
    assert verify_checked(db, history)["verified"]
    apply_checked(db, history, expected_digest=history["digest"], source_plan=plan)
    assert counts == {m: db.scalar(select(func.count()).select_from(m)) for m in counts}
    assert db.scalar(select(SinglesSongArtwork)).song_id == song.id
    db.delete(song)
    db.flush()
    db.expire_all()
    assert not db.scalars(select(SinglesSongArtwork)).all()
    apply_checked(db, history, expected_digest=history["digest"], source_plan=plan)
    assert not db.scalars(select(SinglesSong)).all()
