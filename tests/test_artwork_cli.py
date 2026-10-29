"""Canonical private artwork plans and CLI output redaction."""

import json
from copy import deepcopy

import pytest

from sidetrack.artwork import main, write
from sidetrack.artwork_recovery import preview, validate
from sidetrack.external.artwork import ArtworkError

pytestmark = pytest.mark.unit


def test_deterministic_preview_and_tamper_rejection():
    class Unavailable:
        def discover(self, target, review):
            return {"target": target, "status": "unavailable"}

    targets = [{"kind": "song", "id": "b"}, {"kind": "album", "id": "a"}]
    plan = preview(targets, Unavailable())
    assert preview(list(reversed(targets)), Unavailable()) == plan
    validate(plan, "artwork-preview")
    changed = deepcopy(plan)
    changed["entries"][0]["status"] = "ready"
    with pytest.raises(ArtworkError):
        validate(changed, "artwork-preview")


def test_private_output_never_overwrites(tmp_path):
    path = tmp_path / "plan.json"
    write(path, {"test": True})
    assert json.loads(path.read_text()) == {"test": True}
    with pytest.raises(FileExistsError):
        write(path, {})


def test_cli_failure_does_not_echo_private_file(tmp_path, capsys):
    path = tmp_path / "private-token-name.json"
    path.write_text("not valid json")
    assert main(["preview", "--inventory", str(path), "--output", str(tmp_path / "out")]) == 1
    output = capsys.readouterr()
    assert "private-token-name" not in output.err
    assert "not valid json" not in output.err
