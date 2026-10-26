"""Supported and legacy entrypoints remain explicit and safe."""

import subprocess
import sys


def test_retired_worker_exits_with_actionable_message():
    process = subprocess.run(
        [sys.executable, "-m", "services.worker"], capture_output=True, text=True, timeout=5
    )
    assert process.returncode != 0
    assert "python -m sidetrack.worker" in process.stderr
    assert "Spotify sync and audio features are unavailable" in process.stderr


def test_supported_and_legacy_help():
    for module in ["sidetrack.worker", "sidetrack.rq_worker", "services.api.rq_worker"]:
        process = subprocess.run(
            [sys.executable, "-m", module, "--help"], capture_output=True, text=True, timeout=5
        )
        assert process.returncode == 0
        assert "--queues" in process.stdout
