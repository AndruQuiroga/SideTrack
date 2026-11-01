"""Spec: analysis/sound-dimensions: selection, components, stability, mood overlap, names."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from audio_lab.dimensions import load_selection, select_tracks
from audio_lab.manifest import COLUMNS, Asset, read_manifest
from audio_lab.runs import EMBEDDINGS, RUN_JSON, load_run

MODEL = "muq-mulan"


def sha(index: int) -> str:
    return f"{index:064x}"


def write_run(path: Path, vectors: np.ndarray, kinds: list[str] | None = None) -> Path:
    """A run whose asset ``i`` has hash ``sha(i)`` and vector ``vectors[i]``."""

    path.mkdir(parents=True)
    rows: dict[str, list] = {k: [] for k in ("run_id", "model", "sha256", "kind", "dim", "vector")}
    for index, vector in enumerate(vectors):
        kind = (kinds or ["full"] * len(vectors))[index]
        values = (path.name, MODEL, sha(index), kind, len(vector), vector.tolist())
        for key, value in zip(rows, values, strict=True):
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
    record = {"run_id": path.name, "models": {MODEL: {"status": "ok", "revision": "r1"}}}
    (path / RUN_JSON).write_text(json.dumps(record), "utf-8")
    return path


def write_manifest(path: Path, rows: list[tuple]) -> Path:
    """Rows of (index, artist, title, kind, duration)."""

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        for index, artist, title, kind, seconds in rows:
            writer.writerow(
                [f"{index}.wav", sha(index), kind, "test", f"ref{index}", seconds, "confirmed"]
                + ["", artist, title]
            )
    return path


def write_seeds(path: Path, rows: list[tuple[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["artist", "title", "album", "youtube_id", "deezer_id"])
        writer.writerows([(a, t, "", "", "") for a, t in rows])
    return path


# Tracks: A (full 0 + preview 1), B (preview only 2), C (full 3), D (control, full 4), E (full 5)
SELECTION_ROWS = [
    (0, "Artist A", "One", "full", 200),
    (1, "Artist A", "One", "preview", 30),
    (2, "Artist B", "Two", "preview", 30),
    (3, "Artist C", "Three", "full", 180),
    (4, "Artist D", "Control", "full", 210),
    (5, "Artist E", "Five", "full", 190),
]


def _selection(tmp_path, seeds=False):
    vectors = np.arange(6 * 4, dtype=float).reshape(6, 4)
    run = write_run(tmp_path / "run", vectors, [r[3] for r in SELECTION_ROWS])
    manifest = write_manifest(tmp_path / "manifest.csv", SELECTION_ROWS)
    table = load_run(run)[1]
    keys = {"artist d|control"} if seeds else set()
    return vectors, select_tracks(table, read_manifest(manifest), MODEL, keys)


def test_full_preferred_over_preview(tmp_path):
    vectors, selection = _selection(tmp_path)

    assert sha(0) in selection.hashes
    assert sha(1) not in selection.hashes
    assert sha(2) in selection.hashes  # a preview stands in when there is no full asset
    row = selection.hashes.index(sha(0))
    assert np.allclose(selection.vectors[row], vectors[0])
    assert isinstance(selection.assets[0], Asset)


def test_control_seeds_excluded(tmp_path):
    _, selection = _selection(tmp_path, seeds=True)

    assert sha(4) not in selection.hashes
    assert len(selection.hashes) == 4

    seeds = write_seeds(tmp_path / "control-seeds.csv", [("ARTIST D!", "control")])
    _, from_files = load_selection(tmp_path / "run", tmp_path / "manifest.csv", MODEL, [seeds])
    assert sha(4) not in from_files.hashes


def test_drop_counts_reported(tmp_path):
    _, selection = _selection(tmp_path, seeds=True)

    assert selection.dropped["preview_superseded"] == 1
    assert selection.dropped["excluded_seed"] == 1
    assert selection.counts()["tracks"] == 4
