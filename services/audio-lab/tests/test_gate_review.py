"""The owner review page: offline, self-contained, and its export is importable."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest
from test_gate import neighbours

from audio_lab import gate
from audio_lab.cli import main
from audio_lab.gate_review import build_data, render, write_review


def record_with_examples(tmp_path):
    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "a.wav").write_bytes(b"RIFF")
    record = neighbours()
    record["examples"] = [
        {"id": "e1", "label": "Seed A and neighbour", "category": "obscure", "audio": "a.wav"},
        {
            "id": "e2",
            "label": "Seed B and neighbour",
            "category": "altered",
            "audio": "missing.wav",
        },
        {"id": "e3", "label": "Seed C", "shown": "Nearest: track D"},
    ]
    return record, audio


def test_page_is_self_contained(tmp_path):
    record, audio = record_with_examples(tmp_path)
    page = write_review(record, tmp_path / "review.html", audio).read_text(encoding="utf-8")
    assert not re.search(r"https?://|//cdn|@import|<link|<iframe|<script[^>]*\ssrc=", page)
    assert not re.search(r"fetch\(|XMLHttpRequest|WebSocket|EventSource", page)
    assert page.count("<script") == 2  # inline data and inline code only
    data = json.loads(re.search(r'id="data" type="application/json">(.*?)</script>', page, re.S)[1])
    assert data["examples"][0]["audio"].startswith("file://")
    assert data["examples"][1]["audio"] is None  # a missing file is not linked
    assert data["examples"][2]["audio"] is None
    assert "/*__GATE_DATA__*/" not in page


def test_page_escapes_script_terminators(tmp_path):
    record, audio = record_with_examples(tmp_path)
    record["examples"][2]["shown"] = "</script><b>x</b>"
    page = render(build_data(record, audio))
    assert page.count("</script>") == 2


def test_review_command(tmp_path):
    record, audio = record_with_examples(tmp_path)
    source, out = tmp_path / "record.json", tmp_path / "review.html"
    source.write_text(json.dumps(record), encoding="utf-8")
    assert main(["gate", "review", str(source), "--out", str(out), "--audio-dir", str(audio)]) == 0
    assert "Export decision.json" in out.read_text(encoding="utf-8")


def exported(tmp_path, state: dict) -> dict:
    page = write_review(neighbours(), tmp_path / "review.html").read_text(encoding="utf-8")
    function = re.search(r"function buildDecision.*?\n}\n", page, re.S)[0]
    script = f"{function}\nconsole.log(JSON.stringify(buildDecision({json.dumps(state)})));"
    done = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is needed to run the page's code")
def test_decision_export(tmp_path):
    state = {
        "examples": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}],
        "verdicts": {
            "e1": {"verdict": "right"},
            "e2": {"verdict": "wrong", "correction": "closer to calm"},
        },
        "decision": "correct",
        "notes": "e2 is off",
        "today": "2026-11-01",
    }
    decision = exported(tmp_path, state)
    assert decision == {
        "decision": "correct",
        "decided_at": "2026-11-01",
        "notes": "e2 is off",
        "corrections": [{"example_id": "e2", "correction": "closer to calm"}],
        "reviewed_examples": 2,
    }
    # What the page exports is exactly what `gate decide` accepts.
    updated = gate.import_decision(neighbours(), decision)
    assert gate.derive_status(updated) == "gate_pending"
    assert updated["decision"]["corrections"][0]["example_id"] == "e2"
