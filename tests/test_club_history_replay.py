"""Only new reviewed source keys grow history; changed or erased keys never overwrite."""

from copy import deepcopy

from history_support import sample_plan, seal
from sqlalchemy import delete, func, select

from sidetrack.club import HistorySource, SinglesRating, SinglesSession, Week
from sidetrack.club.history.application import apply_checked
from sidetrack.club.history.check import check_plan
from sidetrack.identity import User


def apply_plan(db, plan):
    checked = check_plan(db, plan)
    assert not checked["conflicts"], checked["conflicts"]
    return apply_checked(db, checked, expected_digest=checked["digest"], source_plan=plan)


def test_expanded_export_reuses_sources_and_adds_only_new_rating(db):
    plan = sample_plan()
    apply_plan(db, plan)
    before_ids = set(db.scalars(select(HistorySource.source_key)))
    expanded = deepcopy(plan)
    expanded["source_digest"] = "e" * 64
    expanded["records"][0]["fields"]["ratings_thread_id"] = "120"
    final = deepcopy(expanded["records"][-1])
    final.update(key="singles_rating:1:300:303", message_id="303", evidence_hash="f" * 64)
    final["fields"].update(phase="final", value=4.5)
    expanded["records"].append(final)
    apply_plan(db, seal(expanded))
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(Week)) == 1
    assert db.scalar(select(func.count()).select_from(SinglesRating)) == 2
    assert set(db.scalars(select(HistorySource.source_key))) == before_ids | {final["key"]}
    assert db.scalar(select(Week)).ratings_thread_id == "120"
    assert not check_plan(db, expanded)["conflicts"]


def test_all_erased_replay_does_not_provision_authors(db):
    plan = sample_plan()
    apply_plan(db, plan)
    db.delete(db.scalar(select(User)))
    db.flush()
    db.expire_all()
    db.execute(delete(Week))
    db.execute(delete(SinglesSession))
    db.expire_all()
    checked = check_plan(db, plan)
    assert not checked["conflicts"]
    assert checked["identities"] == {}
    assert checked["albums"] == {}
    assert all(row["action"] == "erased" for row in checked["records"])
    apply_plan(db, plan)
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert db.scalar(select(func.count()).select_from(Week)) == 0
    assert db.scalar(select(func.count()).select_from(HistorySource)) == 8
