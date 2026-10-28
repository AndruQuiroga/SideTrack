"""Postgres provenance constraints and additive historical-week behavior."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sidetrack.club import HistoryBatch, HistorySource, Week


def batch(db):
    item = HistoryBatch(
        guild_id="1",
        plan_digest=uuid.uuid4().hex,
        source_digest="b" * 64,
        parser_version=1,
        counts={"week": 1},
    )
    db.add(item)
    db.flush()
    return item


def test_existing_week_creation_defaults_to_non_historical(db):
    week = Week(label="Live week", week_number=1)
    db.add(week)
    db.flush()
    db.refresh(week)
    assert week.historical is False


def test_source_identity_is_unique_and_does_not_depend_on_filename(db):
    run = batch(db)
    values = {
        "source_key": "week:1:10:10",
        "batch_id": run.id,
        "kind": "week",
        "thread_id": "10",
        "message_id": None,
        "evidence_hash": "e" * 64,
        "target_kind": "week",
        "target_id": uuid.uuid4(),
        "target_hash": "t" * 64,
    }
    db.add(HistorySource(**values))
    db.flush()
    db.add(HistorySource(**values))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_deleted_target_keeps_minimal_replay_marker(db):
    run = batch(db)
    week = Week(label="Imported", historical=True)
    db.add(week)
    db.flush()
    marker = HistorySource(
        source_key="week:1:10:10",
        batch_id=run.id,
        kind="week",
        thread_id="10",
        evidence_hash="e" * 64,
        target_kind="week",
        target_id=week.id,
        target_hash="t" * 64,
    )
    db.add(marker)
    db.flush()
    db.delete(week)
    db.flush()
    assert db.scalar(select(HistorySource.source_key)) == "week:1:10:10"
    assert not {"author_name", "author_id", "review", "raw_message", "path"}.intersection(
        HistorySource.__table__.columns.keys()
    )
