"""Recovery atomicity, preconditions and safe retries on real Postgres."""

from copy import deepcopy

import pytest
from artwork_support import ready_plan
from sqlalchemy import select

from sidetrack.artwork_models import ArtworkRecovery
from sidetrack.artwork_recovery import apply, check, reverse, seal, verify
from sidetrack.catalog import Album, AlbumArtwork
from sidetrack.external.artwork import ArtworkError


def album(db, title="Synthetic Album"):
    row = Album(title=title, artist_name="Synthetic Artist")
    db.add(row)
    db.flush()
    return row


def test_apply_verify_retry_and_guarded_reversal(db):
    row = album(db)
    checked = check(db, ready_plan(db))
    receipt = apply(db, checked, checked["digest"])
    assert receipt.plan_digest == checked["digest"]
    assert verify(db, checked)["verified"]
    assert apply(db, checked, checked["digest"]).plan_digest == receipt.plan_digest
    assert len(db.scalars(select(AlbumArtwork)).all()) == 1
    reverse(db, checked, checked["digest"])
    assert row.cover_url is None
    reverse(db, checked, checked["digest"])
    assert not db.scalars(select(AlbumArtwork)).all()
    with pytest.raises(ArtworkError):
        apply(db, checked, checked["digest"])


def test_stale_target_and_digest_rejected_atomically(db):
    first, second = album(db), album(db, "Other Album")
    checked = check(db, ready_plan(db))
    with pytest.raises(ArtworkError):
        apply(db, checked, "0" * 64)
    second.cover_url = "https://i.scdn.co/image/concurrent"
    db.flush()
    with pytest.raises(ArtworkError, match="changed"):
        apply(db, checked, checked["digest"])
    assert first.cover_url is None
    assert not db.scalars(select(AlbumArtwork)).all()
    assert not db.scalars(select(ArtworkRecovery)).all()


def test_mid_write_failure_has_no_partial_writes(db, monkeypatch):
    import sidetrack.artwork_recovery as implementation

    first, second = album(db), album(db, "Other Album")
    checked = check(db, ready_plan(db))
    original = implementation.WRITE["album"]
    calls = []

    def fail(*args):
        calls.append(1)
        if len(calls) == 2:
            raise ArtworkError("Synthetic write failure")
        original(*args)

    monkeypatch.setitem(implementation.WRITE, "album", fail)
    with pytest.raises(ArtworkError):
        apply(db, checked, checked["digest"])
    db.expire_all()
    assert first.cover_url is None and second.cover_url is None
    assert not db.scalars(select(ArtworkRecovery)).all()
    assert not db.scalars(select(AlbumArtwork)).all()


def test_changed_evidence_blocks_retry_and_reversal(db):
    album(db)
    checked = check(db, ready_plan(db))
    apply(db, checked, checked["digest"])
    art = db.scalar(select(AlbumArtwork))
    art.evidence = {"altered": True}
    db.flush()
    assert not verify(db, checked)["verified"]
    with pytest.raises(ArtworkError):
        reverse(db, checked, checked["digest"])


def test_deleted_target_is_never_recreated(db):
    row = album(db)
    checked = check(db, ready_plan(db))
    apply(db, checked, checked["digest"])
    db.delete(row)
    db.flush()
    db.expire_all()
    assert verify(db, checked)["erased"] == 1
    apply(db, checked, checked["digest"])
    assert not db.scalars(select(Album)).all()
    assert not db.scalars(select(AlbumArtwork)).all()
    with pytest.raises(ArtworkError):
        reverse(db, checked, checked["digest"])


def test_duplicate_targets_and_existing_covers(db):
    row = album(db)
    plan = ready_plan(db)
    duplicate = deepcopy(plan)
    duplicate["entries"] *= 2
    with pytest.raises(ArtworkError, match="Duplicate"):
        check(db, seal(duplicate))
    row.cover_url = "https://i.scdn.co/image/existing"
    db.flush()
    with pytest.raises(ArtworkError, match="changed"):
        check(db, plan)
