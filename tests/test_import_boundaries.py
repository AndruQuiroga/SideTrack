"""Exercise the actual CI boundary guard, including deliberately illegal imports."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.unit


def run_linter(root):
    env = {**os.environ, "PYTHONPATH": str(root), "NO_COLOR": "1"}
    return subprocess.run(
        [shutil.which("lint-imports"), "--no-cache"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_real_package_keeps_import_contracts():
    result = run_linter(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "illegal_import",
    [
        "from sidetrack.catalog.models import Track",
        "from sidetrack.api.main import create_app",
    ],
)
def test_guard_rejects_private_or_transport_import(tmp_path, illegal_import):
    # Work on a disposable copy so negative tests never edit the real workspace.
    for package in ["sidetrack", "services"]:
        shutil.copytree(
            ROOT / package,
            tmp_path / package,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    (tmp_path / "sidetrack/listening/_illegal.py").write_text(illegal_import + "\n")
    result = run_linter(tmp_path)
    assert result.returncode != 0, result.stdout
    assert "BROKEN" in result.stdout, result.stdout + result.stderr
    assert "sidetrack.listening._illegal" in result.stdout
