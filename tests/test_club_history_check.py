"""Target checks are read-only and bind review decisions to current stored state."""

from copy import deepcopy

import pytest
from history_support import sample_plan, seal
from sqlalchemy import event, select

from sidetrack.catalog import ensure_historical_album
from sidetrack.club import HistoryBatch, HistorySource, Rating, Week
from sidetrack.club.history.check import check_plan, validate_checked
from sidetrack.club.history.sources import HistoryError
from sidetrack.club.history.store import target_hash
from sidetrack.identity import User, ensure_historical_identity


def test_check_never_executes_writes_and_is_deterministic(db):
    statements = []

    def capture(connection, cursor, statement, parameters, context, many):
        statements.append(statement.split()[0].upper())

    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        first = check_plan(db, sample_plan())
        assert first == check_plan(db, sample_plan())
        validate_checked(first)
        assert not first["conflicts"]
        assert len(first["records"]) == 8
        assert first["identities"]["200"]["action"] == "create"
        assert len(first["albums"]) == 1
        assert all(r["action"] == "new" for r in first["records"])
        assert not ({"INSERT", "UPDATE", "DELETE"} & set(statements))
        assert not db.new and not db.dirty and not db.deleted
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)


def test_unresolved_review_and_unapproved_identity_are_visible_conflicts(db):
    plan = sample_plan()
    plan["issues"] = [{"source": "301", "reason": "Unknown submitter"}]
    plan["identities"]["200"]["decision"] = None
    checked = check_plan(db, seal(plan))
    assert any(r["reason"] == "Unknown submitter" for r in checked["conflicts"])
    assert any("explicit reviewed create" in r["reason"] for r in checked["conflicts"])
    assert db.scalars(select(User)).all() == []


def test_exact_discord_identity_reused_and_fingerprint_changes_with_profile(db):
    user = ensure_historical_identity(
        db, discord_id="200", display_name="Existing", allow_create=True
    )
    first = check_plan(db, sample_plan())
    assert first["identities"]["200"]["user_id"] == str(user.id)
    user.display_name = "Changed"
    db.flush()
    second = check_plan(db, sample_plan())
    assert first["digest"] != second["digest"]
    assert not second["conflicts"]


def test_existing_week_and_handle_are_conflicts(db):
    db.add_all(
        [
            Week(label="Manual week", week_number=1),
            User(handle="discord_200", display_name="Independent user"),
        ]
    )
    db.flush()
    checked = check_plan(db, sample_plan())
    assert any("independently stored" in r["reason"] for r in checked["conflicts"])
    assert any("handle is already in use" in r["reason"] for r in checked["conflicts"])


def marked_week(db):
    plan = sample_plan()
    plan["records"] = [plan["records"][0]]
    seal(plan)
    week = Week(label="Week 001", week_number=1, historical=True, nominations_thread_id="100")
    batch = HistoryBatch(
        guild_id="1", plan_digest="b" * 64, source_digest="a" * 64, parser_version=1, counts={}
    )
    db.add_all([week, batch])
    db.flush()
    row = plan["records"][0]
    db.add(
        HistorySource(
            source_key=row["key"],
            batch_id=batch.id,
            kind="week",
            thread_id="100",
            evidence_hash=row["evidence_hash"],
            target_kind="week",
            target_id=week.id,
            target_hash=target_hash(week),
        )
    )
    db.flush()
    return plan, week


def test_changed_source_mapping_or_target_is_a_conflict(db):
    plan, week = marked_week(db)
    assert not check_plan(db, plan)["conflicts"]
    altered = deepcopy(plan)
    altered["records"][0]["evidence_hash"] = "c" * 64
    assert "source evidence" in check_plan(db, seal(altered))["conflicts"][0]["reason"]
    altered = deepcopy(plan)
    altered["records"][0]["fields"]["label"] = "Reinterpreted"
    assert "interpretation differs" in check_plan(db, seal(altered))["conflicts"][0]["reason"]
    week.label = "Manually edited"
    db.flush()
    assert "target has changed" in check_plan(db, plan)["conflicts"][0]["reason"]


def test_expanded_sources_only_fill_previously_empty_week_thread_references(db):
    plan, week = marked_week(db)
    plan["records"][0]["fields"]["ratings_thread_id"] = "120"
    checked = check_plan(db, seal(plan))
    assert not checked["conflicts"]
    assert checked["records"][0]["action"] == "extend"
    assert week.ratings_thread_id is None


def test_pending_writes_and_tampered_plan_are_rejected(db):
    plan = sample_plan()
    plan["guild_id"] = "2"
    with pytest.raises(HistoryError, match="digest"):
        check_plan(db, plan)
    db.add(User(display_name="Pending"))
    with pytest.raises(HistoryError, match="clean session"):
        check_plan(db, sample_plan())


def test_existing_user_rating_on_reused_week_is_never_overwritten(db):
    plan, week = marked_week(db)
    full = sample_plan()
    # Keep the same source-backed week while adding its explicitly reviewed winner/rating.
    plan["records"].extend(r for r in full["records"] if r["kind"] in {"winner", "rating"})
    user = ensure_historical_identity(
        db, discord_id="200", display_name="Existing", allow_create=True
    )
    album = ensure_historical_album(
        db, title="Synthetic Album", artist_name="Synthetic Artist", release_year=2026
    )
    db.add(Rating(week_id=week.id, user_id=user.id, album_id=album.id, value=2))
    db.flush()
    checked = check_plan(db, seal(plan))
    assert any("independently stored" in r["reason"] for r in checked["conflicts"])
    assert db.scalar(select(Rating.value)) == 2
