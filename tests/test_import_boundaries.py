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
        # Authorization reads membership only through club's public package.
        "from sidetrack.club.membership import is_member",
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


def test_identity_reads_club_membership_publicly():
    """identity.auth → club is allowed only through the public package (ADR 0009)."""
    source = (ROOT / "sidetrack/identity/auth.py").read_text(encoding="utf-8")
    assert "from sidetrack.club import is_member, member_role" in source
    assert "sidetrack.club.membership" not in source
    assert "sidetrack.club.models" not in source
