import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterable

import numpy as np


# ----------------------------------------------------------------------------
# GPU statistics helpers

def _gpu_stats() -> tuple[float, float]:
    """Return (utilization %, memory MB) for the first visible GPU.

    Falls back to (0.0, 0.0) if no GPU or pynvml is unavailable.
    """

    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = float(pynvml.nvmlDeviceGetUtilizationRates(handle).gpu)
        mem = float(pynvml.nvmlDeviceGetMemoryInfo(handle).used) / (1024 ** 2)
        pynvml.nvmlShutdown()
        return util, mem
    except Exception:
        return 0.0, 0.0


# ----------------------------------------------------------------------------
# Benchmark core

def _simulate_work(models: Iterable[str]) -> None:
    """Run a small compute workload per model to approximate extraction."""

    for _ in models:
        # 100x100 matrix multiply (~small but non-trivial)
        a = np.random.rand(100, 100)
        b = np.random.rand(100, 100)
        _ = a @ b


def run_benchmark(n_tracks: int, models: Iterable[str]) -> dict[str, float]:
    """Run the benchmark for ``n_tracks`` across the provided ``models``.

    Parameters
    ----------
    n_tracks:
        Number of tracks to process.
    models:
        Names of embedding models.

    Returns
    -------
    dict[str, float]
        Dictionary with keys ``time``, ``gpu_util``, ``gpu_mem``.
    """

    start = time.perf_counter()
    util0, mem0 = _gpu_stats()
    for _ in range(n_tracks):
        _simulate_work(models)
    util1, mem1 = _gpu_stats()
    end = time.perf_counter()
    util = max(util0, util1)
    mem = max(mem0, mem1)
    return {"time": end - start, "gpu_util": util, "gpu_mem": mem}


# ----------------------------------------------------------------------------
# CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark extraction performance")
    parser.add_argument("--tracks", type=int, default=1, help="number of tracks")
    parser.add_argument(
        "--models", nargs="*", default=["dummy"], help="model names to benchmark"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path(__file__).with_name("bench_extractor_baseline.json"),
        help="path to baseline JSON file",
    )
    parser.add_argument("--update", action="store_true", help="update baseline file")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.2,
        help="relative tolerance before failing (e.g. 0.2 = 20%)",
    )
    args = parser.parse_args(argv)

    metrics = run_benchmark(args.tracks, args.models)
    baseline_path: Path = args.baseline

    if args.update or not baseline_path.exists():
        baseline_path.write_text(json.dumps(metrics, indent=2))
        print("baseline written", file=sys.stderr)
        return 0

    baseline = json.loads(baseline_path.read_text())
    failures: list[str] = []
    for key, value in metrics.items():
        base = float(baseline.get(key, 0.0))
        if base > 0 and value > base * (1 + args.tolerance):
            failures.append(f"{key}: {value:.4f} > {base:.4f}")
    if failures:
        print("performance regression detected", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1

    print(json.dumps(metrics))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual CLI
    raise SystemExit(main())
