"""Spec: analysis/audio-embeddings: production vectors match the benchmark pipeline.

Embeds a sample of an audio-lab run's assets with the production pipeline and compares each
vector with the run's MuQ-MuLan vector for the same SHA-256. Needs a CUDA GPU, the weights,
SIDETRACK_PARITY_RUN_DIR (an audio-lab run directory) and SIDETRACK_AUDIO_DIR.

    docker run --rm --gpus all -v RUN:/parity-run:ro -v AUDIO:/audio:ro -v HF:/hf \
        -e SIDETRACK_PARITY_RUN_DIR=/parity-run -e SIDETRACK_AUDIO_DIR=/audio sidetrack-gpu-test

(Not /run: the NVIDIA runtime hook writes there.)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from sidetrack.analysis.embeddings import audio
from sidetrack.analysis.embeddings.muq_mulan import MuQMuLan
from sidetrack.analysis.embeddings.registry import MAX_FULL_S, MUQ_MULAN

pytestmark = pytest.mark.gpu

SAMPLE = 24
THRESHOLD = 0.999


@pytest.fixture(scope="module")
def benchmark():
    run_dir = os.environ.get("SIDETRACK_PARITY_RUN_DIR")
    audio_dir = os.environ.get("SIDETRACK_AUDIO_DIR")
    if not run_dir or not audio_dir:
        pytest.skip("set SIDETRACK_PARITY_RUN_DIR and SIDETRACK_AUDIO_DIR to an audio-lab run")
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        pytest.skip("no CUDA device")
    pq = pytest.importorskip("pyarrow.parquet")
    run = Path(run_dir)
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    assert record["models"][MUQ_MULAN.name]["revision"] == MUQ_MULAN.revision
    table = pq.read_table(run / "embeddings.parquet").to_pylist()
    rows = sorted(
        (r for r in table if r["model"] == MUQ_MULAN.name), key=lambda r: r["sha256"]
    )
    # Spread the sample over the run, previews and full tracks alike.
    step = max(1, len(rows) // SAMPLE)
    return Path(audio_dir), rows[::step][:SAMPLE], record["run_id"]


def test_vectors_match_the_benchmark_run(benchmark):
    audio_dir, rows, run_id = benchmark
    model = MuQMuLan()
    model.load("cuda:0")
    cosines = {}
    for row in rows:
        [path] = audio_dir.glob(f"{row['sha256']}.*")
        wave = audio.decode(path, MUQ_MULAN.sample_rate)
        max_s = MAX_FULL_S if row["kind"] == "full" else None
        chunks = audio.windows(wave, MUQ_MULAN.sample_rate, max_s=max_s)
        vector = audio.pool(model.embed_windows(chunks))
        expected = np.asarray(row["vector"], dtype=np.float64)
        cosines[row["sha256"]] = float(
            np.dot(vector, expected) / (np.linalg.norm(vector) * np.linalg.norm(expected))
        )
    below = {sha: c for sha, c in cosines.items() if c < THRESHOLD}
    print(f"{len(cosines)} assets from {run_id}: min cosine {min(cosines.values()):.6f}")
    assert len(cosines) == len(rows) and not below, below
