"""Gate records, checks and summaries. Every record here is synthetic."""

from __future__ import annotations

import copy
import json

import pytest

from audio_lab import gate
from audio_lab.cli import main

COVERAGE = {
    "total_items": 200,
    "evaluated": 183,
    "missing_audio": 0,
    "ambiguous_links": 0,
    "short_files": 12,
    "model_failures": 5,
    "unknown_or_abstained": 3,
    "rater_disagreement": 4,
    "excluded_other": [],
}


def base(task: str, **section) -> dict:
    return {
        "record_id": "rec-001",
        "claim": "synthetic-claim",
        "task": task,
        "claim_wording": "Sounds like the seed",
        "model": "synthetic-model",
        "checkpoint_revision": "abc123",
        "probe_revision": "none",
        "pipeline": "pipeline-v1",
        "vocabulary": "synthetic vocabulary",
        "vocabulary_version": "v1",
        "preprocessing": "mono 24 kHz",
        "source": "preview",
        "analyzed_duration_s": 30,
        "time_range": "first 30 s",
        "population": {"items": 200, "artists": 150},
        "evaluated_on": "2026-10-31",
        "datasets": [],
        "raters": 1,
        "challenge": {"held_out": True, "obscure": 40, "electronic": 60, "altered": 10},
        "fits": False,
        "coverage": copy.deepcopy(COVERAGE),
        "robustness": {
            "material_change": 0.1,
            "sampling_unit": "track",
            "uncertainty": {"ci95": [0.4, 0.5]},
            "preview_vs_full": {"delta": 0.02},
        },
        "declared_at": "2026-10-30T10:00:00",
        "scored_at": "2026-10-31T10:00:00",
        task: section,
    }


def neighbours() -> dict:
    return base(
        "neighbours",
        pairwise_judgments={"count": 100, "blind": True},
        ranking={"name": "precision@5", "value": 0.46},
        random_control={"precision": 0.05},
        recent_or_frequent_baseline={"precision": 0.2},
        judgments=[
            {"seed": "s1", "neighbour": "n1", "verdict": "similar"},
            {"seed": "s1", "neighbour": "n2", "verdict": "not_similar"},
        ],
    )


def text_label() -> dict:
    return base(
        "text_label",
        prompt_variants={"calm": ["calm music", "a calm track"], "dark": ["dark", "a dark song"]},
        hard_negatives={"count": 20},
        abstention={"supported": True, "abstained": 3},
        raw_vs_relative={
            "raw_cosine": {"accuracy": 0.6},
            "library_relative": {"accuracy": 0.7},
        },
    )


def axis(r2: float) -> dict:
    return {
        "r2": r2,
        "mean_only_baseline_r2": 0.0,
        "rank_correlation": 0.8,
        "calibration_coverage": 0.9,
    }


def mood() -> dict:
    record = base(
        "mood",
        axes={"valence": axis(0.6), "arousal": axis(0.7)},
        axis_correlation={"predicted_library": 0.5, "human": 0.57},
    )
    record["fits"] = True
    record["grouping"] = {"mode": "artist"}
    record["items"] = [
        {"id": "a", "fold": 0, "audio_sha256": "h1", "recording_id": "r1"},
        {"id": "b", "fold": 1, "audio_sha256": "h2", "recording_id": "r2"},
    ]
    return record


def timing() -> dict:
    return base(
        "timing",
        targets=["beats", "tempo", "sections"],
        tolerance_s=0.5,
        boundary_accuracy=0.7,
        label_accuracy=0.6,
        half_double_tempo_agreement=0.9,
        reference_classes=["intro", "verse", "chorus"],
    )


def eras() -> dict:
    return base("eras", periods=12, missing_periods=2, interpolated_periods=0, seed_stability=0.9)


def other() -> dict:
    return base("other", metric_plan="Compare against the owner's labels, 50 items.")


BUILDERS = {
    "neighbours": neighbours,
    "text_label": text_label,
    "mood": mood,
    "timing": timing,
    "eras": eras,
    "other": other,
}


@pytest.mark.parametrize("task", list(BUILDERS))
def test_complete_record_per_task(task):
    result = gate.check_record(BUILDERS[task]())
    assert result["missing"] == []
    assert result["status"] == "complete"


def test_task_section_is_required():
    record = neighbours()
    del record["neighbours"]
    assert "neighbours" in gate.check_record(record)["missing"]


def test_other_needs_a_metric_plan():
    record = other()
    record["other"] = {}
    assert gate.check_record(record)["missing"] == ["metric_plan"]


def test_missing_checkpoint_revision(tmp_path, capsys):
    record = neighbours()
    del record["checkpoint_revision"]
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["checkpoint_revision"]
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert main(["gate", "check", str(path)]) == 1
    assert "checkpoint_revision" in capsys.readouterr().out


def test_every_missing_header_field_is_named():
    record = neighbours()
    for field in ("model", "pipeline", "vocabulary_version", "time_range", "source"):
        del record[field]
    assert set(gate.check_record(record)["missing"]) == {
        "model",
        "pipeline",
        "vocabulary_version",
        "time_range",
        "source",
    }


def test_altered_versions_not_covered():
    record = neighbours()
    record["challenge"] = {"held_out": True, "obscure": 40, "electronic": 60}
    result = gate.check_record(record)
    assert result["not_covered"] == ["altered"]
    assert result["status"] == "complete"
    assert gate.summarize(record)["not_covered"] == ["altered"]


def test_challenge_must_be_held_out():
    record = neighbours()
    record["challenge"]["held_out"] = False
    assert "challenge" in gate.check_record(record)["missing"]


def test_ungrouped_flag():
    record = mood()
    record["grouping"] = {"mode": "none", "reason": "artist metadata unavailable"}
    summary = gate.summarize(record)
    fitted = [m for m in summary["metrics"] if m["fitted"]]
    assert fitted
    assert all(m["caveat"] == "not artist-grouped: scores may be optimistic" for m in fitted)
    assert summary["grouping"] == "none"


def test_ungrouped_needs_a_reason():
    record = mood()
    record["grouping"] = {"mode": "none"}
    assert "grouping" in gate.check_record(record)["missing"]


def test_artist_grouped_has_no_caveat():
    assert all(m["caveat"] is None for m in gate.summarize(mood())["metrics"])


def test_duplicate_hash_across_folds():
    record = mood()
    record["items"][1]["audio_sha256"] = "h1"
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert "duplicate_items" in result["missing"]
    assert any("h1" in m for m in result["messages"])


@pytest.mark.parametrize("key", ["recording_id", "upload_group"])
def test_duplicate_recording_or_upload_across_folds(key):
    record = mood()
    record["items"][0][key] = "same"
    record["items"][1][key] = "same"
    assert "duplicate_items" in gate.check_record(record)["missing"]


def test_duplicate_in_one_fold_is_fine():
    record = mood()
    record["items"][1].update(fold=0, audio_sha256="h1")
    assert gate.check_record(record)["status"] == "complete"


def test_accepted_duplicate_needs_a_reason():
    record = mood()
    record["items"][1]["audio_sha256"] = "h1"
    record["accepted_leakage"] = [{"key": "h1", "reason": ""}]
    assert gate.check_record(record)["status"] == "incomplete"
    record["accepted_leakage"] = [{"key": "h1", "reason": "owner: same file, kept in both"}]
    assert gate.check_record(record)["status"] == "complete"
