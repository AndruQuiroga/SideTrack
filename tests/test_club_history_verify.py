"""Verification reports mismatches without repairing targets or exposing content."""

import json

from history_support import sample_plan
from sqlalchemy import select

from sidetrack.club import SinglesRating
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan
from sidetrack.club.history.store import target_hash
from sidetrack.club.history.verification import verify_checked
from sidetrack.identity import User


def test_verification_detects_mutation_and_never_repairs_it(db):
    unrelated = User(display_name="Untouched account")
    db.add(unrelated)
    db.flush()
    original = target_hash(unrelated)
    plan = sample_plan()
    checked = check_plan(db, plan)
    apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)
    result = verify_checked(db, checked)
    assert result["verified"]
    assert result["counts"] == {"reuse": 8}
    row = db.scalar(select(SinglesRating))
    row.value, row.review = 1, "Private text that must never appear in the report"
    db.flush()
    result = verify_checked(db, checked)
    assert not result["verified"]
    assert "target has changed" in result["mismatches"][0]["reason"]
    assert row.value == 1
    assert not db.new and not db.dirty
    assert "Private text" not in json.dumps(result)
    assert "Synthetic listener" not in json.dumps(result)
    assert target_hash(unrelated) == original
