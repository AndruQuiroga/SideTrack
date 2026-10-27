"""Spec: analysis/audio-benchmark: runs can be compared for parity across hardware."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from audio_lab.cli import main
from audio_lab.parity import ParityError, parity
from audio_lab.runs import EMBEDDINGS, RUN_JSON

WINDOWS = {"window_s": 10.0, "min_tail_s": 3.0, "max_full_s": 180.0, "max_duration_s": None}


def write_run(root: Path, run_id: str, vectors: dict[str, dict[str, list[float]]], **over) -> Path:
    """A run directory with the given model → sha256 → vector rows."""

    path = root / run_id
    path.mkdir(parents=True)
    rows: dict[str, list] = {k: [] for k in ("run_id", "model", "sha256", "kind", "dim", "vector")}
    for model, by_sha in vectors.items():
        for sha, vector in by_sha.items():
            for key, value in zip(
                rows, (run_id, model, sha, "full", len(vector), vector), strict=True
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
    models = {m: {"status": "ok", "revision": over.get("revision", "r1")} for m in vectors}
    record = {"run_id": run_id, "windows": over.get("windows", WINDOWS), "models": models}
    (path / RUN_JSON).write_text(json.dumps(record), encoding="utf-8")
    return path


def unit(*values: float) -> list[float]:
    vector = np.asarray(values, dtype=np.float64)
    return list(vector / np.linalg.norm(vector))


BASE = {"a" * 64: unit(1, 0, 0), "b" * 64: unit(0, 1, 0), "c" * 64: unit(0, 0, 1)}


def test_same_model_on_two_gpus(tmp_path):
    drifted = dict(BASE)
    drifted["b" * 64] = unit(0.05, 1, 0)  # cosine ≈ 0.99875, below 0.999
    drifted["d" * 64] = unit(1, 1, 1)  # only in the second run
    run_a = write_run(tmp_path, "rtx5070", {"muq-mulan": BASE, "muq": BASE})
    run_b = write_run(tmp_path, "gtx1070ti", {"muq-mulan": drifted})

    result = parity(run_a, run_b, "muq-mulan")

    assert result["shared"] == 3 and result["only_in_a"] == 0 and result["only_in_b"] == 1
    assert result["min"] == pytest.approx(0.99875, abs=1e-5)
    assert result["median"] == pytest.approx(1.0)
    assert result["min"] <= result["p1"] <= result["median"]
    assert [row["sha256"] for row in result["below"]] == ["b" * 64]


def test_cli_prints_statistics_and_assets_below_threshold(tmp_path, capsys):
    drifted = dict(BASE)
    drifted["c" * 64] = unit(0, 0.1, 1)
    run_a = write_run(tmp_path, "a", {"muq-mulan": BASE})
    run_b = write_run(tmp_path, "b", {"muq-mulan": drifted})

    assert main(["parity", str(run_a), str(run_b), "--model", "muq-mulan"]) == 0

    out = capsys.readouterr().out
    assert "3 shared assets" in out and "median 1.000000" in out
    assert "1 below 0.999" in out and "c" * 64 in out


def test_different_revisions_are_refused(tmp_path, capsys):
    run_a = write_run(tmp_path, "a", {"muq-mulan": BASE}, revision="2e01c796")
    run_b = write_run(tmp_path, "b", {"muq-mulan": BASE}, revision="ffff0000")

    with pytest.raises(ParityError, match="2e01c796.*ffff0000"):
        parity(run_a, run_b, "muq-mulan")
    assert main(["parity", str(run_a), str(run_b), "--model", "muq-mulan"]) == 1
    assert "revisions differ" in capsys.readouterr().err


def test_different_window_settings_are_refused(tmp_path):
    run_a = write_run(tmp_path, "a", {"muq-mulan": BASE})
    run_b = write_run(tmp_path, "b", {"muq-mulan": BASE}, windows={**WINDOWS, "max_full_s": 60.0})

    with pytest.raises(ParityError, match="window settings differ"):
        parity(run_a, run_b, "muq-mulan")


def test_model_missing_from_a_run(tmp_path, capsys):
    run_a = write_run(tmp_path, "with-muq", {"muq-mulan": BASE, "muq": BASE})
    run_b = write_run(tmp_path, "without-muq", {"muq-mulan": BASE})

    assert main(["parity", str(run_a), str(run_b), "--model", "muq"]) == 1
    assert "run without-muq has no muq embeddings" in capsys.readouterr().err


def test_not_a_run_directory(tmp_path, capsys):
    run_a = write_run(tmp_path, "a", {"muq-mulan": BASE})

    assert main(["parity", str(run_a), str(tmp_path / "nowhere"), "--model", "muq-mulan"]) == 1
    assert "is not a run directory" in capsys.readouterr().err
