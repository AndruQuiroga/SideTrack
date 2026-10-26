"""Spec: analysis/audio-benchmark: runs embed, version, record performance, report failures."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from conftest import HashAdapter, UnloadableAdapter

from audio_lab.adapters import ADAPTERS, ModelUnavailable, get_adapter
from audio_lab.runs import EMBEDDINGS, FAILURES, RUN_JSON, embed_run

THREE = [
    ("A", "One", "full", 12, 220),
    ("B", "Two", "full", 12, 330),
    ("C", "Three", "preview", 6, 440),
]


def _run(manifest, audio_dir, out, adapters=None):
    return embed_run(
        manifest, audio_dir, adapters or [HashAdapter()], out, device="cpu", commit="abc1234"
    )


def test_embedding_a_small_manifest(make_manifest, audio_dir, tmp_path):
    run = _run(make_manifest(THREE), audio_dir, tmp_path / "runs")

    table = pq.read_table(run.path / EMBEDDINGS)
    assert table.num_rows == 3
    assert set(table.column("model").to_pylist()) == {"hash"}
    assert set(table.column("dim").to_pylist()) == {8}
    assert all(len(v) == 8 for v in table.column("vector").to_pylist())
    assert set(table.column("run_id").to_pylist()) == {run.run_id}


def test_missing_file_is_recorded_and_others_embed(make_manifest, audio_dir, tmp_path):
    run = _run(make_manifest(THREE, missing={"Two"}), audio_dir, tmp_path / "runs")

    assert pq.read_table(run.path / EMBEDDINGS).num_rows == 2
    rows = list(csv.DictReader((run.path / FAILURES).open(encoding="utf-8")))
    assert [(r["model"], r["reason"]) for r in rows] == [("hash", "missing_file")]


def test_two_runs_never_overwrite(make_manifest, audio_dir, tmp_path):
    manifest = make_manifest(THREE)
    first = _run(manifest, audio_dir, tmp_path / "runs")
    second = embed_run(
        manifest, audio_dir, [HashAdapter()], tmp_path / "runs", device="cpu", commit="def5678"
    )

    assert first.run_id != second.run_id
    for run in (first, second):
        assert (run.path / RUN_JSON).is_file() and (run.path / EMBEDDINGS).is_file()
    with pytest.raises(FileExistsError):
        first.path.mkdir(exist_ok=False)


def test_run_json_records_versions_and_performance(make_manifest, audio_dir, tmp_path):
    manifest = make_manifest(THREE)
    run = _run(manifest, audio_dir, tmp_path / "runs")
    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))

    assert record["run_id"] == run.run_id and re.match(r"\d{8}-\d{6}-abc1234", run.run_id)
    assert record["git_commit"] == "abc1234"
    assert len(record["manifest"]["sha256"]) == 64 and record["manifest"]["assets"] == 3
    model = record["models"]["hash"]
    for key in ("checkpoint", "revision", "license", "sample_rate", "dim", "pooling", "dtype"):
        assert key in model
    perf = model["performance"]
    # 12 s full tracks keep one 10 s window (the 2 s tail is dropped); the 6 s preview is kept.
    assert perf["audio_seconds"] == pytest.approx(26.0, abs=0.1)
    assert perf["embedded"] == 3 and perf["failed"] == 0
    for key in ("wall_seconds", "audio_seconds_per_second", "peak_vram_mib"):
        assert key in perf
    assert "python" in record["environment"]


def test_unloadable_model_is_reported_not_faked(make_manifest, audio_dir, tmp_path):
    run = _run(
        make_manifest(THREE), audio_dir, tmp_path / "runs", [UnloadableAdapter(), HashAdapter()]
    )

    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))
    assert record["models"]["unloadable"]["status"] == "unavailable"
    assert "weights" in record["models"]["unloadable"]["reason"]
    assert "unloadable" not in pq.read_table(run.path / EMBEDDINGS).column("model").to_pylist()


def test_real_adapters_without_torch_are_unavailable(make_manifest, audio_dir, tmp_path):
    pytest.importorskip("numpy")
    try:
        import torch  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("models extra installed; covered by the gpu tests")
    for name in ADAPTERS:
        with pytest.raises(ModelUnavailable, match="torch is not installed"):
            get_adapter(name).load("cpu")
    run = _run(
        make_manifest(THREE), audio_dir, tmp_path / "runs", [get_adapter(n) for n in ADAPTERS]
    )
    assert pq.read_table(run.path / EMBEDDINGS).num_rows == 0
    record = json.loads((run.path / RUN_JSON).read_text(encoding="utf-8"))
    assert {m["status"] for m in record["models"].values()} == {"unavailable"}


def test_adapters_never_generate_vectors():
    """No random or constant vectors in real adapters (AGENTS.md: no fakes)."""

    source_dir = Path(__file__).parents[1] / "src" / "audio_lab" / "adapters"
    for source in source_dir.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert not re.search(r"\brandom\b|\brandn?\(|\bfull\(|\bones\(", text), source.name
