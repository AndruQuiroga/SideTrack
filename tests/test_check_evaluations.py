"""Spec: analysis/evaluation-gates. The register check, on synthetic trees and on the repo."""

from __future__ import annotations

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_evaluations", ROOT / "scripts" / "check_evaluations.py"
)
check_evaluations = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_evaluations)

TODAY = date(2026, 11, 1)
SEED_IDS = {
    "deam",
    "musav",
    "mtg-jamendo",
    "pmemo",
    "musiccaps",
    "song-describer",
    "muchomusic",
    "jam-alt",
    "harmonix",
}
REVISIONS = {
    "model": "synthetic-model",
    "checkpoint_revision": "abc123",
    "probe_revision": "probe-1",
    "pipeline": "pipeline-v1",
    "vocabulary_version": "v1",
}


def dataset(identifier: str, **overrides) -> dict:
    return {
        "id": identifier,
        "name": identifier.upper(),
        "url": f"https://example.invalid/{identifier}",
        "use": "synthetic",
        "audio_terms": "synthetic terms",
        "annotation_terms": "synthetic terms",
        "status": {"audio": "recorded", "annotations": "recorded"},
        "gaps": [],
        "acquisition": "owner_manual",
        "storage": "HDD, outside the repo",
        "recheck": True,
        "reviewed": date(2026, 10, 31),
        **overrides,
    }


def claim(**overrides) -> dict:
    return {
        "claim": "mood-estimate",
        "title": "Mood estimate",
        "status": "approved",
        "feature_revisions": dict(REVISIONS),
        "datasets": [{"id": "deam", "use": "audio"}],
        "capabilities": ["Track mood scores"],
        "summary": "docs/evaluations/summaries/mood-estimate/rec-1.json",
        **overrides,
    }


def summary(**overrides) -> dict:
    return {
        "claim": "mood-estimate",
        "status": "approved",
        "revisions": dict(REVISIONS),
        "decision": {"decision": "approve", "decided_at": "2026-11-01"},
        **overrides,
    }


def build(tmp_path: Path, claims, datasets=None, works=True, summary_data=None) -> Path:
    directory = tmp_path / "docs" / "evaluations"
    (directory / "summaries" / "mood-estimate").mkdir(parents=True, exist_ok=True)
    datasets = [dataset("deam"), dataset("musav")] if datasets is None else datasets
    (directory / "datasets.yaml").write_text(yaml.safe_dump({"datasets": datasets}), "utf-8")
    (directory / "register.yaml").write_text(yaml.safe_dump({"claims": claims}), "utf-8")
    status = {
        "reviewed": "2026-11-01",
        "groups": [
            {
                "name": "Analysis",
                "items": [
                    {
                        "capability": "Track mood scores",
                        "status": "works" if works else "partial",
                        "evidence": ["x"],
                    }
                ],
            }
        ],
    }
    (tmp_path / "docs" / "status.yaml").write_text(yaml.safe_dump(status), "utf-8")
    if summary_data is not None:
        path = directory / "summaries" / "mood-estimate" / "rec-1.json"
        path.write_text(json.dumps(summary_data), "utf-8")
    return tmp_path


def run(root: Path) -> tuple[list[str], list[str]]:
    return check_evaluations.check(root, TODAY)


def test_seed_datasets_registered():
    data = yaml.safe_load((ROOT / "docs" / "evaluations" / "datasets.yaml").read_text("utf-8"))
    _, errors, warnings = check_evaluations.check_datasets(data, TODAY)
    assert (errors, warnings) == ([], [])
    entries = {d["id"]: d for d in data["datasets"]}
    assert set(entries) == SEED_IDS
    for entry in entries.values():
        assert entry["reviewed"] == date(2026, 10, 31)
        assert entry["acquisition"] == "owner_manual"
        assert entry["recheck"] is True
        assert "outside" in entry["storage"]
    for youtube_only in ("musiccaps", "harmonix"):
        assert entries[youtube_only]["status"]["audio"] == "annotation_only"
    assert entries["deam"]["status"]["audio"] == "rights_unconfirmed"
    assert entries["musav"]["status"]["audio"] == "rights_unconfirmed"
    assert not any("cleared" in str(e).lower() for e in entries.values())


def test_pending_gate_blocks_works(tmp_path):
    root = build(tmp_path, [claim(status="gate_pending", summary=None)])
    errors, _ = run(root)
    assert len(errors) == 1
    assert "mood-estimate" in errors[0] and "gate_pending" in errors[0]
    assert "Track mood scores" in errors[0]


def test_pending_gate_without_works_is_fine(tmp_path):
    root = build(tmp_path, [claim(status="gate_pending", summary=None)], works=False)
    assert run(root) == ([], [])


def test_approved_gate_allows_works(tmp_path):
    root = build(tmp_path, [claim()], summary_data=summary())
    assert run(root) == ([], [])


def test_approved_needs_a_summary_with_an_owner_approve(tmp_path):
    root = build(tmp_path, [claim()])
    assert any("does not exist" in e for e in run(root)[0])
    root = build(tmp_path, [claim()], summary_data=summary(decision=None, status="gate_pending"))
    assert any("owner approve" in e for e in run(root)[0])


def test_stale_pipeline(tmp_path):
    declared = {**REVISIONS, "pipeline": "pipeline-v2"}
    root = build(tmp_path, [claim(feature_revisions=declared)], summary_data=summary())
    errors, _ = run(root)
    assert len(errors) == 1
    assert "stale" in errors[0]
    assert "pipeline-v1" in errors[0] and "pipeline-v2" in errors[0]


def test_declared_stale_status_is_honest(tmp_path):
    declared = {**REVISIONS, "pipeline": "pipeline-v2"}
    stale = claim(status="stale", feature_revisions=declared)
    root = build(tmp_path, [stale], works=False, summary_data=summary())
    assert run(root) == ([], [])
    root = build(tmp_path, [stale], works=True, summary_data=summary())
    assert any("stale" in e and "works" in e for e in run(root)[0])


def test_unregistered_dataset(tmp_path):
    cites = [{"id": "pmemo", "use": "annotations"}]
    root = build(tmp_path, [claim(status="gate_pending", datasets=cites)], works=False)
    errors, _ = run(root)
    assert len(errors) == 1
    assert "pmemo" in errors[0] and "incomplete" in errors[0]
    root = build(tmp_path, [claim(status="incomplete", datasets=cites)], works=False)
    assert run(root) == ([], [])


def test_unregistered_dataset_cannot_be_approved(tmp_path):
    cites = [{"id": "pmemo", "use": "annotations"}]
    root = build(tmp_path, [claim(datasets=cites)], summary_data=summary())
    assert any("pmemo" in e for e in run(root)[0])


def test_rights_unconfirmed_blocks_approval(tmp_path):
    musav = dataset("musav", status={"audio": "rights_unconfirmed", "annotations": "recorded"})
    cites = [{"id": "musav", "use": "audio"}]
    root = build(tmp_path, [claim(datasets=cites)], datasets=[musav], summary_data=summary())
    errors, _ = run(root)
    assert len(errors) == 1
    assert "MUSAV" in errors[0] and "mood-estimate" in errors[0]
    assert "rights_unconfirmed" in errors[0]


def test_recorded_annotations_do_not_need_audio_rights(tmp_path):
    musav = dataset("musav", status={"audio": "rights_unconfirmed", "annotations": "recorded"})
    cites = [{"id": "musav", "use": "annotations"}]
    root = build(tmp_path, [claim(datasets=cites)], datasets=[musav], summary_data=summary())
    assert run(root) == ([], [])


def test_dataset_use_must_be_stated(tmp_path):
    root = build(tmp_path, [claim(datasets=["deam"])], summary_data=summary())
    assert any("use: audio or annotations" in e for e in run(root)[0])


def test_youtube_only_audio_must_be_annotation_only(tmp_path):
    cap = dataset("musiccaps", audio_source="youtube_reference")
    errors, _ = run(build(tmp_path, [], datasets=[cap]))
    assert any("annotation_only" in e for e in errors)
    held = dict(cap, owner_holds_audio=True)
    assert run(build(tmp_path, [], datasets=[held]))[0] == []


def test_acquisition_is_never_automated(tmp_path):
    bad = dataset("deam", acquisition="yt-dlp scheduled")
    assert any("never automated" in e for e in run(build(tmp_path, [], datasets=[bad]))[0])


def test_storage_must_be_outside_the_repo(tmp_path):
    bad = dataset("deam", storage="docs/evaluations/audio")
    assert any("outside" in e for e in run(build(tmp_path, [], datasets=[bad]))[0])


def test_status_values_are_checked(tmp_path):
    bad_claim = claim(status="done")
    bad_dataset = dataset("deam", status={"audio": "cleared", "annotations": "recorded"})
    errors, _ = run(build(tmp_path, [bad_claim], datasets=[bad_dataset]))
    assert any("status must be one of" in e and "done" in e for e in errors)
    assert any("status.audio" in e for e in errors)


def test_old_review_warns(tmp_path):
    old = dataset("deam", reviewed=date(2025, 1, 1))
    errors, warnings = run(build(tmp_path, [], datasets=[old]))
    assert errors == []
    assert any("deam" in w and "365" in w for w in warnings)


def test_unknown_capability_is_an_error(tmp_path):
    root = build(tmp_path, [claim(capabilities=["Typo"], status="incomplete", summary=None)])
    assert any("'Typo'" in e for e in run(root)[0])


def test_every_claim_needs_all_revisions(tmp_path):
    thin = claim(status="incomplete", summary=None, feature_revisions={"model": "m"})
    assert any("feature_revisions" in e for e in run(build(tmp_path, [thin]))[0])


def test_duplicate_claims(tmp_path):
    one = claim(status="incomplete", summary=None)
    assert any("duplicate" in e for e in run(build(tmp_path, [one, copy.deepcopy(one)]))[0])


def test_seed_register_is_honest_and_consistent():
    assert check_evaluations.check(ROOT, TODAY) == ([], [])
    data = yaml.safe_load((ROOT / "docs" / "evaluations" / "register.yaml").read_text("utf-8"))
    claims = {c["claim"]: c for c in data["claims"]}
    assert claims["muq-mulan-neighbours"]["status"] == "incomplete"
    assert claims["mood-estimate"]["status"] == "incomplete"
    assert claims["muq-mulan-neighbours"]["feature_revisions"]["pipeline"] == (
        "w10-t3-cap180-fp32-mean-l2-v1"
    )
    assert "20261031-204732-9b07ff0" in json.dumps(claims["mood-estimate"]["evidence"])
