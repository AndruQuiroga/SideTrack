"""Gate records, checks and summaries. Every record here is synthetic."""

from __future__ import annotations

import copy
import json
import os
import shlex
import socket
import subprocess
from pathlib import Path

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


def test_neighbour_requires_random_control():
    record = neighbours()
    del record["neighbours"]["random_control"]
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["random_control"]


def test_neighbour_requires_recent_or_frequent_baseline():
    record = neighbours()
    del record["neighbours"]["recent_or_frequent_baseline"]
    assert gate.check_record(record)["missing"] == ["recent_or_frequent_baseline"]


def test_neighbour_judgments_must_be_blind():
    record = neighbours()
    record["neighbours"]["pairwise_judgments"]["blind"] = False
    assert gate.check_record(record)["missing"] == ["pairwise_judgments"]


def test_preview_counted_as_same_recording():
    record = neighbours()
    record["neighbours"]["judgments"].append(
        {"seed": "s1", "neighbour": "s1-preview", "verdict": "similar", "is_seed_preview": True}
    )
    derived = gate.check_record(record)["derived"]
    assert derived["same_recording"] == 1
    # The preview is not a correct "sounds similar" neighbour: 1 of the other 2.
    assert derived["judged_for_similarity"] == 2
    assert derived["similar_precision"] == 0.5


def test_version_of_seed_counted_as_same_recording():
    record = neighbours()
    record["neighbours"]["judgments"].append(
        {"seed": "s1", "neighbour": "n9", "verdict": "similar", "is_version_of_seed": True}
    )
    assert gate.check_record(record)["derived"]["same_recording"] == 1


def test_single_prompt_incomplete():
    record = text_label()
    record["text_label"]["prompt_variants"]["calm"] = ["calm music"]
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["prompt_variants"]


@pytest.mark.parametrize("task", ["text_label", "neighbours"])
def test_similarity_called_confidence(task):
    record = BUILDERS[task]()
    record["claim_wording"] = "Matches the theme with 80% confidence"
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["uncalibrated_confidence"]


def test_text_label_requires_hard_negatives_and_abstention():
    record = text_label()
    del record["text_label"]["hard_negatives"]
    record["text_label"]["abstention"] = {"supported": False}
    assert set(gate.check_record(record)["missing"]) == {"hard_negatives", "abstention"}


def test_mood_requires_both_axes():
    record = mood()
    del record["mood"]["axes"]["arousal"]
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["arousal"]


def test_mood_requires_baseline_ranking_and_calibration():
    record = mood()
    for name in ("mean_only_baseline_r2", "rank_correlation", "calibration_coverage"):
        del record["mood"]["axes"]["valence"][name]
    assert set(gate.check_record(record)["missing"]) == {
        "valence.mean_only_baseline_r2",
        "valence.rank_correlation",
        "valence.calibration_coverage",
    }


def test_axis_correlation_warning():
    record = mood()
    record["mood"]["axis_correlation"] = {"predicted_library": 0.92, "human": 0.57}
    result = gate.check_record(record)
    assert result["status"] == "complete"
    assert any("may not be distinguished" in w for w in result["warnings"])
    summary = gate.summarize(record)
    assert any("0.92" in w and "0.57" in w for w in summary["warnings"])


def test_low_axis_correlation_has_no_warning():
    assert not any("distinguished" in w for w in gate.check_record(mood())["warnings"])


def test_timing_requires_tolerance():
    record = timing()
    del record["timing"]["tolerance_s"]
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["tolerance_s"]


def test_timing_reports_boundary_and_label_accuracy_separately():
    record = timing()
    del record["timing"]["label_accuracy"]
    assert gate.check_record(record)["missing"] == ["label_accuracy"]


def test_tempo_requires_half_double_agreement():
    record = timing()
    del record["timing"]["half_double_tempo_agreement"]
    assert gate.check_record(record)["missing"] == ["half_double_tempo_agreement"]


def test_drop_label_unsupported():
    record = timing()
    record["claim_wording"] = "Marks the drop in electronic tracks"
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["unsupported_label"]
    record["timing"]["reference_classes"].append("drop")
    assert gate.check_record(record)["status"] == "complete"


def test_eras_never_interpolate_missing_periods():
    record = eras()
    record["eras"]["interpolated_periods"] = 1
    assert gate.check_record(record)["missing"] == ["interpolated_periods"]


def test_failure_counts():
    result = gate.check_record(neighbours())
    coverage = result["coverage"]
    assert coverage["model_failures"] == 5
    assert coverage["short_files"] == 12
    assert coverage["excluded"] == 17
    assert coverage["excluded_fraction"] == "17/200"
    assert coverage["excluded_fraction_value"] == 0.085


def test_coverage_counts_must_add_up():
    record = neighbours()
    record["coverage"]["evaluated"] = 190
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert "coverage_counts" in result["missing"]


def test_other_exclusions_count_with_a_reason():
    record = neighbours()
    record["coverage"]["evaluated"] = 173
    record["coverage"]["excluded_other"] = [{"reason": "duplicate of seed", "count": 10}]
    assert gate.check_record(record)["coverage"]["excluded_fraction"] == "27/200"


def test_missing_coverage_count_is_named():
    record = neighbours()
    del record["coverage"]["ambiguous_links"]
    assert gate.check_record(record)["missing"] == ["coverage"]


def test_preview_robustness_flag():
    record = neighbours()
    record["robustness"]["preview_vs_full"] = {"delta": -0.15}
    result = gate.check_record(record)
    assert result["status"] == "complete"
    assert result["flags"] == ["preview_robustness_failed"]
    assert gate.summarize(record)["flags"] == ["preview_robustness_failed"]


def test_preview_within_material_change_is_not_flagged():
    assert gate.check_record(neighbours())["flags"] == []


def test_preview_not_applicable_needs_a_reason():
    record = neighbours()
    record["robustness"]["preview_vs_full"] = {"not_applicable": "no full audio exists"}
    assert gate.check_record(record)["status"] == "complete"
    record["robustness"]["preview_vs_full"] = {}
    assert gate.check_record(record)["missing"] == ["preview_vs_full"]


@pytest.mark.parametrize("unit", ["play", "listen", None])
def test_play_level_resampling_rejected(unit):
    record = neighbours()
    record["robustness"]["sampling_unit"] = unit
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["sampling_unit"]


def test_thresholds_declared_after_scoring():
    record = neighbours()
    record["declared_at"] = "2026-11-01T00:00:00"
    result = gate.check_record(record)
    assert result["status"] == "incomplete"
    assert result["missing"] == ["declared_at"]


def test_thresholds_never_declared():
    record = neighbours()
    del record["declared_at"]
    assert gate.check_record(record)["missing"] == ["declared_at"]


def test_material_change_must_be_declared():
    record = neighbours()
    del record["robustness"]["material_change"]
    assert gate.check_record(record)["missing"] == ["material_change"]


def decision(kind: str, **extra) -> dict:
    return {
        "decision": kind,
        "decided_at": "2026-11-01",
        "notes": "heard 20 examples",
        "corrections": [],
        "reviewed_examples": 20,
        **extra,
    }


def test_no_decision_is_pending():
    record = neighbours()
    assert gate.derive_status(record) == "gate_pending"
    assert gate.summarize(record)["status"] == "gate_pending"


def test_dataset_scores_without_owner_review_are_pending():
    record = mood()
    record["datasets"] = ["deam"]
    assert gate.derive_status(record) == "gate_pending"


def test_approve():
    record = gate.import_decision(neighbours(), decision("approve"))
    assert gate.derive_status(record) == "approved"
    assert gate.summarize(record)["decision"]["decision"] == "approve"


def test_approve_does_not_rescue_an_incomplete_record():
    record = neighbours()
    del record["checkpoint_revision"]
    record = gate.import_decision(record, decision("approve"))
    assert gate.derive_status(record) == "incomplete"


def test_reject():
    record = gate.import_decision(neighbours(), decision("reject", notes="sounds wrong"))
    assert gate.derive_status(record) == "rejected"
    assert record["decision"]["notes"] == "sounds wrong"


def test_reject_needs_a_note():
    with pytest.raises(gate.GateError, match="note"):
        gate.import_decision(neighbours(), decision("reject", notes=""))


def test_correct_stays_pending():
    fixes = [{"example_id": str(i), "correction": "calm"} for i in range(3)]
    record = gate.import_decision(neighbours(), decision("correct", corrections=fixes))
    assert gate.derive_status(record) == "gate_pending"
    assert record["decision"]["corrections"] == fixes
    record = gate.import_decision(record, decision("approve"))
    assert gate.derive_status(record) == "approved"
    assert record["decision_history"][0]["corrections"] == fixes


def test_correct_needs_corrections():
    with pytest.raises(gate.GateError, match="corrected"):
        gate.import_decision(neighbours(), decision("correct"))


def test_decision_needs_reviewed_examples_and_a_date():
    with pytest.raises(gate.GateError, match="reviewed_examples"):
        gate.import_decision(neighbours(), decision("approve", reviewed_examples=0))
    with pytest.raises(gate.GateError, match="decided_at"):
        gate.import_decision(neighbours(), decision("approve", decided_at="soon"))
    with pytest.raises(gate.GateError, match="decision must be"):
        gate.import_decision(neighbours(), decision("maybe"))


def test_decide_command_writes_updated_record(tmp_path):
    record, owner, out = tmp_path / "r.json", tmp_path / "d.json", tmp_path / "out.json"
    record.write_text(json.dumps(neighbours()), encoding="utf-8")
    owner.write_text(json.dumps(decision("approve")), encoding="utf-8")
    assert main(["gate", "decide", str(record), str(owner), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["decision"]["decision"] == "approve"


REPO = Path(gate.__file__).resolve().parents[4]


def test_refuses_repo_output(tmp_path, capsys):
    record = tmp_path / "record.json"
    record.write_text(json.dumps(neighbours()), encoding="utf-8")
    inside = REPO / "scratch-gate-output.json"
    for argv in (
        ["gate", "check", str(record), "--out", str(inside)],
        ["gate", "summarize", str(record), "--out", str(inside)],
        ["gate", "review", str(record), "--out", str(inside)],
        ["gate", "decide", str(record), str(record), "--out", str(inside)],
    ):
        assert main(argv) == 1
        assert "inside the repository" in capsys.readouterr().err
        assert not inside.exists()


def test_summaries_may_go_to_the_summary_directory(tmp_path):
    record = tmp_path / "record.json"
    record.write_text(json.dumps(neighbours()), encoding="utf-8")
    allowed = REPO / "docs" / "evaluations" / "summaries" / "claim" / "x.json"
    gate.ensure_output_allowed(allowed, summary=True)
    with pytest.raises(gate.OutputInRepo):
        gate.ensure_output_allowed(allowed, summary=False)
    with pytest.raises(gate.OutputInRepo):
        gate.ensure_output_allowed(REPO / "docs" / "elsewhere.json", summary=True)


def personal_record() -> dict:
    record = mood()
    record["items"] = [
        {"id": "Secret Title.flac", "fold": 0, "audio_sha256": "h1", "artist": "Secret Artist"},
        {"id": "/home/owner/music/b.flac", "fold": 1, "audio_sha256": "h2"},
    ]
    record["grouping"] = {"mode": "artist", "reason": "see /home/owner/notes.txt"}
    record["examples"] = [{"id": "1", "label": "Secret Artist - Secret Title", "audio": "a/b.flac"}]
    record["mood"]["per_track"] = {"Secret Title": {"valence": 0.3}}
    return gate.import_decision(
        record,
        decision("correct", notes="Secret Title felt wrong", corrections=[{"example_id": "1"}]),
    )


def test_summary_has_no_titles_or_paths():
    text = json.dumps(gate.summarize(personal_record()))
    for leaked in ("Secret", "/home/owner", ".flac", "felt wrong", 'valence": 0.3'):
        assert leaked not in text
    summary = json.loads(text)
    assert summary["claim"] == "synthetic-claim"
    assert summary["revisions"]["checkpoint_revision"] == "abc123"
    assert summary["decision"]["corrections"] == 1
    assert {"name": "axes.valence.r2", "value": 0.6} == {
        k: v for k, v in summary["metrics"][0].items() if k in ("name", "value")
    }


def test_summary_refuses_a_path_in_a_revision_field():
    record = mood()
    record["probe_revision"] = "/home/owner/probe.joblib"
    with pytest.raises(gate.GateError, match="probe_revision"):
        gate.summarize(record)
    record["probe_revision"] = "../probe"
    with pytest.raises(gate.GateError, match="probe_revision"):
        gate.summarize(record)


def test_summary_of_an_incomplete_record_says_so():
    record = mood()
    del record["pipeline"]
    summary = gate.summarize(record)
    assert summary["status"] == "incomplete"
    assert summary["missing"] == ["pipeline"]


def test_one_rater_summary_is_scoped_to_the_owner():
    assert gate.summarize(mood())["scope"] == "owner library only"
    record = mood()
    record["raters"] = 3
    assert gate.summarize(record)["scope"] is None


def test_summarize_command(tmp_path):
    record, out = tmp_path / "record.json", tmp_path / "summary.json"
    record.write_text(json.dumps(personal_record()), encoding="utf-8")
    assert main(["gate", "summarize", str(record), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["record_id"] == "rec-001"


def test_readme_example(tmp_path):
    readme = (REPO / "services" / "audio-lab" / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Evaluation gates", 1)[1]
    block = section.split("```bash\n", 1)[1].split("```", 1)[0]
    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "x1.wav").write_bytes(b"RIFF")
    record = neighbours()
    record["examples"] = [{"id": "1", "label": "Synthetic pair", "audio": "x1.wav"}]
    files = {
        "$RECORD": tmp_path / "record.json",
        "$DECISION": tmp_path / "decision.json",
        "$DECIDED": tmp_path / "decided.json",
        "$REVIEW": tmp_path / "review.html",
        "$SUMMARY": tmp_path / "summary.json",
        "$METADATA": tmp_path / "metadata.csv",
        "$AUDIO": audio,
    }
    files["$RECORD"].write_text(json.dumps(record), encoding="utf-8")
    files["$DECISION"].write_text(json.dumps(decision("approve")), encoding="utf-8")
    files["$METADATA"].write_text("id,caption\nx1,a\nx2,b\n", encoding="utf-8")
    commands = [line for line in block.splitlines() if line.strip()]
    assert [shlex.split(c)[4] for c in commands] == [
        "check",
        "review",
        "decide",
        "summarize",
        "prepare",
    ]
    for line in commands:
        argv = [str(files.get(t, t)) for t in shlex.split(line)]
        assert argv[:3] == ["uv", "run", "audio-lab"], line
        assert main(argv[3:]) == 0, line
    assert json.loads(files["$SUMMARY"].read_text())["status"] == "approved"


def test_youtube_dataset_prepares_no_audio(tmp_path, monkeypatch, capsys):
    """MusicCaps metadata without local audio: nothing is prepared, fetched or started."""

    def forbidden(*args, **kwargs):
        raise AssertionError("evaluation preparation must not start a process or connection")

    for target in ("run", "Popen", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, target, forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    metadata = tmp_path / "musiccaps.csv"
    metadata.write_text("id,caption\nyt1,a\nyt2,b\nyt3,c\n", encoding="utf-8")
    result = gate.prepare_annotation_only(metadata, None)
    assert result == {
        "items": 3,
        "local_audio": 0,
        "no_local_audio": 3,
        "audio_prepared": 0,
        "downloads_started": 0,
    }
    assert main(["gate", "prepare", "--metadata", str(metadata)]) == 0
    assert '"no_local_audio": 3' in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.iterdir()) == ["musiccaps.csv"]


def test_prepare_counts_only_audio_the_owner_holds(tmp_path):
    held = tmp_path / "held"
    held.mkdir()
    (held / "yt2.wav").write_bytes(b"RIFF")
    metadata = tmp_path / "m.csv"
    metadata.write_text("id\nyt1\nyt2\n", encoding="utf-8")
    result = gate.prepare_annotation_only(metadata, held)
    assert (result["local_audio"], result["no_local_audio"]) == (1, 1)


def test_prepare_needs_the_id_column(tmp_path):
    metadata = tmp_path / "m.csv"
    metadata.write_text("ytid\nyt1\n", encoding="utf-8")
    with pytest.raises(gate.GateError, match="id"):
        gate.prepare_annotation_only(metadata, None)
