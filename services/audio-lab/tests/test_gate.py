"""Gate records, checks and summaries. Every record here is synthetic."""

from __future__ import annotations

import copy

import pytest

from audio_lab import gate

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
