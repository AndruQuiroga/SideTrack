"""Spec: analysis/audio-benchmark: mood probes, comparison and predictions, on synthetic runs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from audio_lab import mood
from audio_lab.cli import main
from audio_lab.manifest import COLUMNS
from audio_lab.mood import MoodError, RidgePath, group_folds, mood_probe, predict_run
from audio_lab.runs import EMBEDDINGS, RUN_JSON
from audio_lab.seeds import OutputInRepo, repo_root

CLIPS = 120
DIM = 16


def _write_run(path: Path, models: dict[str, np.ndarray], *, revision: str = "r1") -> Path:
    path.mkdir(parents=True)
    rows: dict[str, list] = {k: [] for k in ("run_id", "model", "sha256", "kind", "dim", "vector")}
    for model, matrix in models.items():
        for index, vector in enumerate(matrix):
            for key, value in zip(
                rows,
                (path.name, model, f"{index:064x}", "full", len(vector), vector.tolist()),
                strict=True,
            ):
                rows[key].append(value)
    schema = pa.schema(
        [
            ("run_id", pa.string()),
            ("model", pa.string()),
            ("sha256", pa.string()),
            ("kind", pa.string()),
            ("dim", pa.int32()),
            ("vector", pa.list_(pa.float32())),
        ]
    )
    pq.write_table(pa.table(rows, schema=schema), path / EMBEDDINGS)
    record = {
        "run_id": path.name,
        "models": {name: {"status": "ok", "revision": revision} for name in models},
    }
    (path / RUN_JSON).write_text(json.dumps(record), "utf-8")
    return path


def _write_labels(path: Path, y: np.ndarray, groups: list[str] | None = None) -> Path:
    groups = groups or [f"clip:{i}" for i in range(len(y))]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("sha256", "valence", "arousal", "group"))
        for index, ((valence, arousal), group) in enumerate(zip(y, groups, strict=True)):
            writer.writerow((f"{index:064x}", valence, arousal, group))
    return path


def _signal(seed: int = 1, clips: int = CLIPS, noise: float = 0.02) -> tuple:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(clips, DIM))
    weights = rng.normal(size=(DIM, 2))
    y = x @ weights + rng.normal(scale=noise, size=(clips, 2))
    return x, y


def test_ridge_recovers_linear_signal():
    x, y = _signal()

    prediction = RidgePath(x, y).predict(x, 1e-3)

    assert np.abs(prediction - y).max() < 0.2


def test_groups_never_cross_folds():
    groups = np.array([f"artist:{i % 17}" for i in range(CLIPS)])

    assignment = group_folds(groups, 5, np.random.default_rng(0))

    for group in np.unique(groups):
        assert len(set(assignment[groups == group])) == 1
    sizes = np.bincount(assignment)
    assert sizes.max() - sizes.min() <= 12


def test_signal_scores_high(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    scores = report["models"]["good"]
    assert scores["valence"]["r2_mean"] > 0.9
    assert scores["arousal"]["r2_mean"] > 0.9


def test_shuffled_labels_score_near_zero(tmp_path):
    x, y = _signal()
    rng = np.random.default_rng(5)
    run = _write_run(tmp_path / "run", {"good": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", rng.permutation(y)))

    assert report["models"]["good"]["mean_r2"] <= 0.05


def test_baseline_is_reported_and_near_zero(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    assert -0.1 <= report["models"]["good"]["valence"]["baseline_r2"] <= 0


def test_alpha_uses_training_clips_only(tmp_path, monkeypatch):
    x, y = _signal()
    original = mood.choose_alphas
    seen = []

    def spy(x_train, y_train, groups, rng):
        seen.append({row.tobytes() for row in x_train})
        return original(x_train, y_train, groups, rng)

    monkeypatch.setattr(mood, "choose_alphas", spy)
    groups = np.array([f"clip:{i}" for i in range(CLIPS)])

    predictions, _ = mood.cross_validate(x, y, groups, 5, 1, seed=3)

    assert predictions.shape == (1, CLIPS, 2)
    assert len(seen) == 5
    assert all(len(rows) < CLIPS for rows in seen)
    assignment = group_folds(groups, 5, np.random.default_rng(3))
    held_out = {row.tobytes() for row in x[assignment == 0]}
    assert sum(not (rows & held_out) for rows in seen) == 1


def test_results_are_repeatable(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x, "other": x[::-1]})
    labels = _write_labels(tmp_path / "labels.csv", y)

    first = mood_probe(run, labels, seed=4)
    second = mood_probe(run, labels, seed=4)

    assert first == second


def test_mood_json_records_provenance(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x[:100]})
    labels = _write_labels(tmp_path / "labels.csv", y)

    mood_probe(run, labels, seed=7)

    stored = json.loads((run / "mood.json").read_text("utf-8"))
    assert stored["run_id"] == "run"
    assert len(stored["labels_sha256"]) == 64
    assert (stored["clips"], stored["unmatched_labels"]) == (100, 20)
    assert (stored["seed"], stored["folds"], stored["repeats"]) == (7, 5, 5)
    assert stored["models"]["good"]["revision"] == "r1"
    assert stored["models"]["good"]["valence"]["r2_std"] >= 0


def test_model_not_in_run_fails(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})

    with pytest.raises(MoodError, match="missing"):
        mood_probe(run, _write_labels(tmp_path / "labels.csv", y), ["missing"])

    assert not (run / "mood.json").exists()


def test_too_few_clips_is_unavailable(tmp_path):
    x, y = _signal(clips=20)
    run = _write_run(tmp_path / "run", {"good": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    model = report["models"]["good"]
    assert model["status"] == "unavailable"
    assert model["clips"] == 20
    assert "r2_mean" not in json.dumps(model)


def test_clear_winner_is_ahead(tmp_path):
    x, y = _signal()
    noise = np.random.default_rng(9).normal(size=x.shape)
    run = _write_run(tmp_path / "run", {"noise": noise, "good": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    [comparison] = report["comparisons"]
    assert comparison["ahead"] == "good"
    assert comparison["ci_high"] < 0


def test_equal_models_tie(tmp_path):
    x, y = _signal(noise=1.0)
    run = _write_run(tmp_path / "run", {"one": x, "two": x})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    [comparison] = report["comparisons"]
    assert comparison["ahead"] is None
    assert comparison["ci_low"] <= 0 <= comparison["ci_high"]


def test_comparison_uses_only_shared_clips(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"one": x, "two": x[:100]})

    report = mood_probe(run, _write_labels(tmp_path / "labels.csv", y))

    assert report["clips"] == 100


def test_predicts_second_run(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})
    target = _write_run(tmp_path / "library", {"good": x[:7]})
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, COLUMNS, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerow(
            {
                "path": "a.mp3",
                "sha256": f"{0:064x}",
                "kind": "full",
                "source": "test",
                "source_id": "1",
                "verification": "unverified",
                "artist": "Band",
                "title": "Song",
            }
        )
    out = tmp_path / "predictions" / "mood.csv"

    count = predict_run(
        run, _write_labels(tmp_path / "labels.csv", y), target, out, manifest=manifest
    )

    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert count == len(rows) == 7
    assert (rows[0]["artist"], rows[0]["title"]) == ("Band", "Song")
    assert abs(float(rows[0]["valence"]) - y[0, 0]) < 0.3


def test_refuses_other_revision(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})
    target = _write_run(tmp_path / "library", {"good": x}, revision="r2")
    out = tmp_path / "mood.csv"

    with pytest.raises(MoodError, match="revision"):
        predict_run(run, _write_labels(tmp_path / "labels.csv", y), target, out)

    assert not out.exists()


def test_predictions_refused_in_repo(tmp_path):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})
    target = _write_run(tmp_path / "library", {"good": x})
    root = repo_root(Path(__file__).resolve().parent)
    assert root is not None

    with pytest.raises(OutputInRepo):
        predict_run(run, _write_labels(tmp_path / "labels.csv", y), target, root / "mood.csv")


def test_cli_probes_and_predicts(tmp_path, capsys):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})
    target = _write_run(tmp_path / "library", {"good": x[:5]})
    labels = _write_labels(tmp_path / "labels.csv", y)
    out = tmp_path / "mood.csv"

    code = main(
        [
            "mood-probe",
            str(run),
            "--labels",
            str(labels),
            "--predict-run",
            str(target),
            "--predict-out",
            str(out),
        ]
    )

    assert code == 0
    assert "good" in capsys.readouterr().out
    assert out.is_file()


def test_cli_reports_a_missing_model(tmp_path, capsys):
    x, y = _signal()
    run = _write_run(tmp_path / "run", {"good": x})
    labels = _write_labels(tmp_path / "labels.csv", y)

    code = main(["mood-probe", str(run), "--labels", str(labels), "--model", "missing"])

    assert code == 1
    assert "missing" in capsys.readouterr().err
