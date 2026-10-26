"""Embedding runs: one new directory per run, never overwritten (ADR 0004)."""

from __future__ import annotations

import csv
import json
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import audio
from .adapters import Adapter, ModelUnavailable, pool
from .manifest import Asset, file_sha256, read_manifest

EMBEDDINGS = "embeddings.parquet"
RUN_JSON = "run.json"
FAILURES = "failures.csv"


@dataclass
class ModelResult:
    status: str  # "ok" or "unavailable"
    reason: str | None = None
    info: dict | None = None
    audio_seconds: float = 0.0
    wall_seconds: float = 0.0
    peak_vram_mib: float = 0.0
    embedded: int = 0
    failed: int = 0

    def as_dict(self) -> dict:
        throughput = self.audio_seconds / self.wall_seconds if self.wall_seconds else 0.0
        return {
            "status": self.status,
            "reason": self.reason,
            **(self.info or {}),
            "performance": {
                "audio_seconds": round(self.audio_seconds, 2),
                "wall_seconds": round(self.wall_seconds, 2),
                "audio_seconds_per_second": round(throughput, 2),
                "peak_vram_mib": round(self.peak_vram_mib, 1),
                "embedded": self.embedded,
                "failed": self.failed,
            },
        }


@dataclass
class Run:
    run_id: str
    path: Path
    models: dict[str, ModelResult] = field(default_factory=dict)


def git_commit(repo: Path | None = None) -> str:
    git = shutil.which("git")
    if git is None:
        return "unknown"
    result = subprocess.run(
        [git, "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=repo
    )
    return result.stdout.strip() or "unknown"


def environment() -> dict:
    env: dict = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import torch
    except ImportError:
        return env
    env.update(torch=torch.__version__, cuda=torch.version.cuda)
    if torch.cuda.is_available():
        env["gpu"] = torch.cuda.get_device_name(0)
        smi = shutil.which("nvidia-smi")
        if smi:
            query = [smi, "--query-gpu=driver_version", "--format=csv,noheader"]
            out = subprocess.run(query, capture_output=True, text=True)
            env["driver"] = out.stdout.strip().splitlines()[0] if out.stdout.strip() else None
    return env


def new_run_dir(out_root: Path, commit: str) -> tuple[str, Path]:
    out_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{commit}"
    path = out_root / run_id
    path.mkdir(exist_ok=False)
    return run_id, path


def embed_run(
    manifest_path: Path,
    audio_dir: Path,
    adapters: list[Adapter],
    out_root: Path,
    *,
    device: str = "cuda",
    commit: str | None = None,
) -> Run:
    """Embed every manifest asset with every adapter; write Parquet, failures and run.json."""

    assets = read_manifest(manifest_path)
    commit = commit or git_commit(Path(__file__).resolve().parent)
    run_id, path = new_run_dir(out_root, commit)
    run = Run(run_id, path)
    started = datetime.now(UTC)
    rows: dict[str, list] = {k: [] for k in ("run_id", "model", "sha256", "kind", "dim", "vector")}
    failures: list[tuple[str, str, str]] = []

    for adapter in adapters:
        try:
            info = adapter.load(device)
        except ModelUnavailable as exc:
            run.models[adapter.name] = ModelResult("unavailable", reason=str(exc))
            continue
        result = ModelResult("ok", info=info.as_dict())
        adapter.reset_peak_memory()
        began = time.perf_counter()
        for asset in assets:
            reason = _embed_asset(adapter, info.sample_rate, asset, audio_dir, rows, run_id, result)
            if reason:
                result.failed += 1
                failures.append((adapter.name, asset.sha256, reason))
        result.wall_seconds = time.perf_counter() - began
        result.peak_vram_mib = adapter.peak_memory_mib()
        adapter.unload()
        run.models[adapter.name] = result

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
    with (path / FAILURES).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "sha256", "reason"])
        writer.writerows(failures)
    record = {
        "run_id": run_id,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        "device": device,
        "manifest": {
            "path": str(manifest_path),
            "sha256": file_sha256(manifest_path),
            "assets": len(assets),
        },
        "windows": {
            "window_s": audio.WINDOW_S,
            "min_tail_s": audio.MIN_TAIL_S,
            "max_full_s": audio.MAX_FULL_S,
        },
        "environment": environment(),
        "models": {name: result.as_dict() for name, result in run.models.items()},
    }
    (path / RUN_JSON).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return run


def _embed_asset(
    adapter: Adapter,
    sample_rate: int,
    asset: Asset,
    audio_dir: Path,
    rows: dict[str, list],
    run_id: str,
    result: ModelResult,
) -> str | None:
    file = audio_dir / asset.path
    if not file.is_file():
        return "missing_file"
    try:
        wave = audio.decode(file, sample_rate)
    except audio.DecodeError:
        return "decode_error"
    max_s = (adapter.max_full_s or audio.MAX_FULL_S) if asset.kind == "full" else None
    chunks = audio.windows(wave, sample_rate, max_s=max_s)
    try:
        vector = pool(adapter.embed_windows(chunks))
    except Exception:  # one bad asset must not end the run; it is recorded
        return "embed_error"
    rows["run_id"].append(run_id)
    rows["model"].append(adapter.name)
    rows["sha256"].append(asset.sha256)
    rows["kind"].append(asset.kind)
    rows["dim"].append(int(vector.shape[0]))
    rows["vector"].append(vector.astype(np.float32).tolist())
    result.embedded += 1
    result.audio_seconds += sum(len(c) for c in chunks) / sample_rate
    return None


def load_run(path: Path) -> tuple[dict, pa.Table]:
    record = json.loads((path / RUN_JSON).read_text(encoding="utf-8"))
    return record, pq.read_table(path / EMBEDDINGS)
