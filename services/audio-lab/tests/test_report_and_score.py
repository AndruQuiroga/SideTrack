"""Spec: the report captures the owner's judgement; scoring summarises agreement."""

from __future__ import annotations

import json
import re

from conftest import HashAdapter

from audio_lab.cli import main
from audio_lab.report import write_report
from audio_lab.runs import embed_run
from audio_lab.score import score

ROWS = [
    ("Broadcast", "Papercuts", "full", 12, 220),
    ("Broadcast", "Papercuts", "preview", 5, 220),
    ("Stereolab", "French Disko", "full", 12, 330),
    ("Portishead", "Roads", "full", 12, 440),
]


def _report(make_manifest, audio_dir, tmp_path):
    manifest = make_manifest(ROWS)
    run = embed_run(
        manifest, audio_dir, [HashAdapter()], tmp_path / "runs", device="cpu", commit="abc1234"
    )
    return run, write_report(run.path, manifest, audio_dir)


def test_report_is_self_contained(make_manifest, audio_dir, tmp_path):
    run, report = _report(make_manifest, audio_dir, tmp_path)
    html = report.read_text(encoding="utf-8")

    assert not re.search(r"<(script|link|img)[^>]+(src|href)=\"https?://", html)
    assert "fonts.googleapis" not in html
    assert run.run_id in html
    for artist in ("Broadcast", "Stereolab", "Portishead"):
        assert artist in html
    data = json.loads(html.split("const DATA = ", 1)[1].split(";\nconst KEY", 1)[0])
    assert data["models"] == ["hash"]
    assert all(s["audio"].startswith("file:///") for s in data["seeds"])
    broadcast = next(s for s in data["seeds"] if s["artist"] == "Broadcast")
    assert len(broadcast["neighbours"]["hash"]) == 2  # the other two seeds, never itself
    assert data["retrieval"]["hash"]["seeds"] == 1


def _verdicts(path, run_id, entries):
    path.write_text(json.dumps({"run_id": run_id, "verdicts": entries}), encoding="utf-8")
    return path


def test_scoring_counts_agreement(tmp_path):
    entries = (
        [{"seed": f"s{i}", "model": "muq", "verdict": "good"} for i in range(8)]
        + [{"seed": f"b{i}", "model": "muq", "verdict": "bad"} for i in range(2)]
        + [{"seed": "u", "model": "muq", "verdict": "unsure"}]
    )
    result = score(_verdicts(tmp_path / "v.json", "run-1", entries), "run-1")
    assert result["muq"] == {"good": 8, "bad": 2, "unsure": 1, "agreement": 0.8}


def test_scoring_refuses_another_runs_verdicts(make_manifest, audio_dir, tmp_path, capsys):
    run, _ = _report(make_manifest, audio_dir, tmp_path)
    verdicts = _verdicts(tmp_path / "v.json", "20990101-000000-other", [])

    assert main(["score", str(run.path), "--verdicts", str(verdicts)]) == 1
    err = capsys.readouterr().err
    assert "20990101-000000-other" in err and run.run_id in err


def test_score_cli_writes_scores(make_manifest, audio_dir, tmp_path):
    run, _ = _report(make_manifest, audio_dir, tmp_path)
    verdicts = _verdicts(
        tmp_path / "v.json", run.run_id, [{"seed": "x", "model": "hash", "verdict": "good"}]
    )
    assert main(["score", str(run.path), "--verdicts", str(verdicts)]) == 0
    assert json.loads((run.path / "scores.json").read_text())["hash"]["agreement"] == 1.0
