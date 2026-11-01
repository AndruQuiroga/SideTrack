"""Spec: analysis/sound-dimensions: selection, components, stability, mood overlap, names."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from audio_lab.adapters import ModelUnavailable
from audio_lab.adapters.models import MuQMuLanAdapter
from audio_lab.cli import main
from audio_lab.dimensions import (
    analyse,
    encode_terms,
    load_selection,
    mood_overlap,
    parallel_analysis,
    principal_components,
    rotate,
    run_dimensions,
    select_tracks,
)
from audio_lab.manifest import COLUMNS, Asset, read_manifest
from audio_lab.runs import EMBEDDINGS, RUN_JSON, load_run
from audio_lab.seeds import OutputInRepo, repo_root

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


def planted(rng, tracks=300, dim=32, strengths=(6.0, 4.0, 3.0), noise=1.0):
    """Gaussian noise plus one orthogonal planted direction per strength."""

    basis = np.linalg.qr(rng.normal(size=(dim, len(strengths))))[0].T
    raw = rng.normal(size=(tracks, len(strengths)))
    raw -= raw.mean(axis=0)
    # Whitened, so equal strengths give exactly equal variances.
    scores = np.linalg.qr(raw)[0] * np.sqrt(tracks - 1) * np.array(strengths)
    return scores @ basis + rng.normal(scale=noise, size=(tracks, dim)), basis


def test_planted_dimensions_found():
    rng = np.random.default_rng(3)
    x, basis = planted(rng)

    kept, threshold = parallel_analysis(x, np.random.default_rng(0))
    _, axes = principal_components(x)

    assert kept == 3
    assert len(threshold) == 32
    for planted_axis, found in zip(basis, axes[:3], strict=True):
        assert abs(planted_axis @ found) > 0.9


def test_pure_noise_keeps_no_dimensions():
    x = np.random.default_rng(5).normal(size=(300, 32))

    kept, _ = parallel_analysis(x, np.random.default_rng(0))

    assert kept == 0


def test_strong_axis_is_stable():
    x, _ = planted(np.random.default_rng(3))

    components = analyse(x, seed=0)

    assert components.kept == 3
    assert components.stability[0] >= 0.95
    assert 0 in components.stable


def test_weak_axis_is_unstable():
    # Two planted directions of equal strength, few tracks for many dimensions: they rotate into
    # each other between resamples.
    x, _ = planted(np.random.default_rng(3), tracks=80, dim=64, strengths=(10.0, 5.0, 5.0))

    components = analyse(x, seed=0)

    assert components.kept == 3
    assert components.stability[0] >= 0.95
    assert components.stability[1] < 0.80 and components.stability[2] < 0.80
    assert components.stable == [0]


def test_results_are_repeatable():
    x, _ = planted(np.random.default_rng(3))

    first, second = analyse(x, seed=7), analyse(x, seed=7)

    assert first.kept == second.kept
    assert np.array_equal(first.stability, second.stability)
    assert np.array_equal(first.threshold, second.threshold)
    assert not np.array_equal(first.stability, analyse(x, seed=8).stability)


def blocks(rng, tracks=400, per_block=4, strengths=(5.0, 5.0, 5.0), noise=0.3):
    """Latent factors that each drive their own block of variables: simple structure."""

    count = len(strengths)
    raw = rng.normal(size=(tracks, count))
    raw -= raw.mean(axis=0)
    scores = np.linalg.qr(raw)[0] * np.sqrt(tracks - 1) * np.array(strengths)
    loadings = np.kron(np.eye(count), np.ones(per_block))  # (count, count * per_block)
    x = scores @ loadings + rng.normal(scale=noise, size=(tracks, count * per_block))
    return x, loadings / np.linalg.norm(loadings, axis=1, keepdims=True)


def test_varimax_recovers_rotated_axes():
    x, truth = blocks(np.random.default_rng(1))
    eigenvalues, axes = principal_components(x)

    rotated, _ = rotate(axes[:3], eigenvalues[:3])

    # Equal-strength factors leave PCA free to mix them; varimax finds the blocks again.
    match = np.abs(rotated @ truth.T)
    assert match.max(axis=1).min() > 0.95
    assert sorted(match.argmax(axis=1)) == [0, 1, 2]


def _mood_case(tracks=200):
    x, _ = planted(np.random.default_rng(3), tracks=tracks)
    _, axes = principal_components(x)
    scores = (x - x.mean(axis=0)) @ axes[:3].T
    rng = np.random.default_rng(9)
    arousal = scores[:, 0] / scores[:, 0].std() + rng.normal(scale=0.2, size=tracks)
    valence = rng.normal(size=tracks)
    hashes = [sha(i) for i in range(tracks)]
    return x, scores, hashes, {h: (v, a) for h, v, a in zip(hashes, valence, arousal, strict=True)}


def test_axis_restating_mood_correlates():
    x, scores, hashes, predictions = _mood_case()

    overlap = mood_overlap(x, scores, hashes, predictions)

    assert overlap["status"] == "ok"
    first, second, _ = overlap["axes"]
    assert abs(first["arousal"]) > 0.9
    assert abs(second["arousal"]) < 0.3 and abs(second["valence"]) < 0.3
    # Arousal follows the 6-strength axis, which holds 36 of the ~100 variance units
    assert 0.2 < overlap["mood_variance_share"] < 0.6


def test_predictions_for_other_tracks_are_counted():
    x, scores, hashes, predictions = _mood_case()
    for sha_ in hashes[:20]:
        del predictions[sha_]
    predictions[sha(9999)] = (0.0, 0.0)

    overlap = mood_overlap(x, scores, hashes, predictions)

    assert overlap["tracks_without_prediction"] == 20
    assert overlap["tracks_with_prediction"] == 180
    assert overlap["predictions_for_other_tracks"] == 1

    sparse = mood_overlap(x, scores, hashes, {hashes[0]: (0.0, 0.0)})
    assert sparse["status"] == "unavailable"


def write_predictions(path: Path, hashes: list[str], valence, arousal) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["sha256", "artist", "title", "model", "valence", "arousal"])
        for h, v, a in zip(hashes, valence, arousal, strict=True):
            writer.writerow([h, "", "", MODEL, v, a])
    return path


def command_inputs(tmp_path, tracks=120):
    """A run of ``tracks`` distinct full tracks with planted structure, a manifest, predictions."""

    x, _ = planted(np.random.default_rng(3), tracks=tracks, dim=16, strengths=(6.0, 4.0))
    run = write_run(tmp_path / "run", x)
    manifest = write_manifest(
        tmp_path / "manifest.csv",
        [(i, f"Artist {i}", f"Title {i}", "full", 200) for i in range(tracks)],
    )
    rng = np.random.default_rng(2)
    predictions = write_predictions(
        tmp_path / "predictions.csv",
        [sha(i) for i in range(tracks)],
        rng.normal(size=tracks),
        rng.normal(size=tracks),
    )
    return run, manifest, predictions


def test_command_writes_provenance(tmp_path):
    run, manifest, predictions = command_inputs(tmp_path)
    out = tmp_path / "out"

    code = main(
        ["dimensions", str(run), "--manifest", str(manifest), "--predictions", str(predictions)]
        + ["--out", str(out), "--seed", "4"]
    )

    report = json.loads((out / "dimensions.json").read_text("utf-8"))
    assert code == 0
    assert report["run_id"] == "run" and report["model"] == MODEL and report["revision"] == "r1"
    assert report["seed"] == 4
    assert report["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert report["predictions_sha256"] == hashlib.sha256(predictions.read_bytes()).hexdigest()
    assert report["selection"]["tracks"] == 120
    assert report["components_kept"] == 2
    assert len(report["axes"]) == report["components_stable"]
    assert report["mood"]["status"] == "ok" and "axes" not in report["mood"]
    assert all("mood" in axis for axis in report["axes"])
    with (out / "scores.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 120
    assert {"sha256", "artist", "title", "pc1", "pc2", "axis1"} <= set(rows[0])
    assert main(["dimensions", str(run), "--manifest", str(manifest), "--out", str(out)]) == 0


def test_output_refused_in_repo(tmp_path, capsys):
    run, manifest, _ = command_inputs(tmp_path)
    out = repo_root(Path(__file__)) / "dimensions-test-output"

    code = main(["dimensions", str(run), "--manifest", str(manifest), "--out", str(out)])

    assert code == 1
    assert "inside the repository" in capsys.readouterr().err
    assert not out.exists()
    with pytest.raises(OutputInRepo):
        run_dimensions(run, manifest, out)


def test_text_unavailable_without_torch(monkeypatch):
    # A None entry makes the import fail, whether or not the models extra is installed.
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "muq", None)

    with pytest.raises(ModelUnavailable, match="torch is not installed"):
        encode_terms(["calm piano"], "cpu")
    with pytest.raises(ModelUnavailable, match="not loaded"):
        MuQMuLanAdapter().embed_texts(["calm piano"])


def test_rotation_keeps_total_variance():
    x, _ = blocks(np.random.default_rng(1), strengths=(6.0, 4.0, 3.0))
    eigenvalues, axes = principal_components(x)

    rotated, variances = rotate(axes[:3], eigenvalues[:3])

    assert variances.sum() == pytest.approx(eigenvalues[:3].sum())
    assert np.allclose(rotated @ rotated.T, np.eye(3), atol=1e-9)
    scores = (x - x.mean(axis=0)) @ rotated.T
    assert np.allclose(scores.var(axis=0, ddof=1), variances)
    assert list(variances) == sorted(variances, reverse=True)
