import json
import subprocess
import sys


def run_script(baseline):
    return subprocess.run(
        [
            sys.executable,
            "scripts/bench_extractor.py",
            "--tracks",
            "1",
            "--models",
            "dummy",
            "--baseline",
            str(baseline),
            "--tolerance",
            "0.2",
        ],
        capture_output=True,
    )


def test_regression_detected(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"time": 1e-6, "gpu_util": 0.0, "gpu_mem": 0.0}))
    result = run_script(baseline)
    assert result.returncode != 0, result.stdout + result.stderr


def test_within_baseline(tmp_path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"time": 100.0, "gpu_util": 0.0, "gpu_mem": 0.0}))
    result = run_script(baseline)
    assert result.returncode == 0, result.stdout + result.stderr
