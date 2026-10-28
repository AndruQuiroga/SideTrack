"""Atomic application, stale checks and safe retry on real Postgres."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from history_support import sample_plan, seal
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from sidetrack.catalog import Album
from sidetrack.club import (
    HistoryBatch,
    HistorySource,
    Nomination,
    Rating,
    SinglesRating,
    SinglesSession,
    SinglesSong,
    SinglesSubmission,
    Week,
)
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan
from sidetrack.club.history.sources import HistoryError
from sidetrack.identity import LinkedAccount, User


def counts(db):
    return {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in (
            User,
            LinkedAccount,
            Album,
            Week,
            Nomination,
            Rating,
            SinglesSession,
            SinglesSong,
            SinglesSubmission,
            SinglesRating,
            HistoryBatch,
            HistorySource,
        )
    }


def apply_plan(db, plan=None):
    plan = plan or sample_plan()
    checked = check_plan(db, plan)
    assert not checked["conflicts"], checked["conflicts"]
    batch = apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    return plan, checked, batch


def test_atomic_application_and_identical_retry(db):
    plan, checked, batch = apply_plan(db)
    before = counts(db)
    assert before["users"] == 1
    assert before["albums"] == 1
    assert before["club_history_sources"] == 8
    assert db.scalar(select(Week)).historical is True
    assert db.scalar(select(Week)).winner_album_id == db.scalar(select(Album.id))
    assert db.scalar(select(Rating)).value == 3.5
    assert db.scalar(select(SinglesRating)).phase == "first"
    again = apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert again.id == batch.id
    assert counts(db) == before


def test_mid_import_failure_rolls_back_identity_catalog_club_and_ledger(db, monkeypatch):
    import sidetrack.club.history.application as implementation

    plan = sample_plan()
    checked = check_plan(db, plan)
    before = counts(db)
    original = implementation.target_fields

    def fail(record, fields, **kwargs):
        if record["kind"] == "rating":
            raise RuntimeError("Synthetic mid-import failure")
        return original(record, fields, **kwargs)

    monkeypatch.setattr(implementation, "target_fields", fail)
    with pytest.raises(RuntimeError, match="mid-import"):
        apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert counts(db) == before


def test_changed_database_and_fresh_source_mismatch_are_rejected(db):
    plan = sample_plan()
    checked = check_plan(db, plan)
    db.add(Week(label="Concurrent week", week_number=1))
    db.flush()
    with pytest.raises(HistoryError, match="Database changed"):
        apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert db.scalars(select(User)).all() == []
    altered = deepcopy(plan)
    altered["records"][0]["fields"]["label"] = "Changed interpretation"
    with pytest.raises(HistoryError, match="Fresh source parsing"):
        apply_checked(db, checked, expected_digest=checked["digest"], source_plan=seal(altered))


def test_retry_after_account_deletion_does_not_resurrect_user_or_contributions(db):
    plan, checked, _ = apply_plan(db)
    db.delete(db.scalar(select(User)))
    db.flush()
    db.expire_all()
    before = counts(db)
    assert before["users"] == 0
    assert before["singles_songs"] == 1
    assert before["singles_ratings"] == 0
    apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert counts(db) == before


def test_edited_imported_target_blocks_retry(db):
    plan, checked, _ = apply_plan(db)
    db.scalar(select(SinglesRating)).value = 1
    db.flush()
    with pytest.raises(HistoryError, match="no longer matches"):
        apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert db.scalar(select(SinglesRating.value)) == 1


def test_apply_holds_guild_lock_until_caller_transaction_finishes(db, engine):
    apply_plan(db)
    with Session(engine) as other:
        assert (
            other.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": "sidetrack:history:1"},
            )
            is False
        )


def test_wrong_digest_and_unresolved_plan_do_not_write(db):
    plan = sample_plan()
    checked = check_plan(db, plan)
    with pytest.raises(HistoryError, match="digest does not match"):
        apply_checked(db, checked, expected_digest="f" * 64, source_plan=plan)
    plan["issues"] = [{"source": "301", "reason": "Synthetic ambiguity"}]
    checked = check_plan(db, seal(plan))
    with pytest.raises(HistoryError, match="Unresolved"):
        apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_committed_concurrent_target_edit_invalidates_checked_plan(engine):
    plan = sample_plan()
    plan["guild_id"] = "999000000000000001"
    plan["records"] = [plan["records"][0]]
    record = plan["records"][0]
    record["key"] = "week:999000000000000001:900:900"
    record["thread_id"] = "900"
    record["fields"].update(
        label=f"Concurrent history {uuid4()}", week_number=None, nominations_thread_id="900"
    )
    seal(plan)
    batch_id = week_id = None
    try:
        with Session(engine) as seed, seed.begin():
            checked = check_plan(seed, plan)
            batch = apply_checked(
                seed, checked, expected_digest=checked["digest"], source_plan=plan
            )
            batch_id = batch.id
            week_id = seed.scalar(
                select(HistorySource.target_id).where(HistorySource.source_key == record["key"])
            )
        with Session(engine) as importer, importer.begin():
            checked = check_plan(importer, plan)
            assert not checked["conflicts"]

            def edit_target():
                with Session(engine) as writer, writer.begin():
                    writer.get(Week, week_id).label = "Edited by concurrent transaction"

            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(edit_target).result(timeout=20)
            with pytest.raises(HistoryError, match="Database changed"):
                apply_checked(
                    importer, checked, expected_digest=checked["digest"], source_plan=plan
                )
        with Session(engine) as inspect:
            assert inspect.get(Week, week_id).label == "Edited by concurrent transaction"
    finally:
        if batch_id is not None:
            with Session(engine) as cleanup, cleanup.begin():
                cleanup.execute(delete(HistorySource).where(HistorySource.batch_id == batch_id))
                cleanup.execute(delete(Week).where(Week.id == week_id))
                cleanup.execute(delete(HistoryBatch).where(HistoryBatch.id == batch_id))
