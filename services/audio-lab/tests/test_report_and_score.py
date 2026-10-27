"""Spec: the owner judges models in blind duels; scoring summarises duel results."""

from __future__ import annotations

import json
import re

import pytest
from conftest import HashAdapter, UnloadableAdapter

from audio_lab.cli import main
from audio_lab.report import write_report
from audio_lab.runs import embed_run
from audio_lab.score import VoteError, score

ROWS = [
    ("Broadcast", "Papercuts", "full", 12, 220),
    ("Broadcast", "Papercuts", "preview", 5, 220),
    ("Stereolab", "French Disko", "full", 12, 330),
    ("Portishead", "Roads", "full", 12, 440),
]


class OtherHashAdapter(HashAdapter):
    """A second test double, so the report has a model pair to duel."""

    name = "hash2"

    def embed_windows(self, batch):
        return super().embed_windows(batch)[:, ::-1].copy()


def _report(make_manifest, audio_dir, tmp_path):
    manifest = make_manifest(ROWS)
    run = embed_run(
        manifest,
        audio_dir,
        [HashAdapter(), OtherHashAdapter(), UnloadableAdapter()],
        tmp_path / "runs",
        device="cpu",
        commit="abc1234",
    )
    return run, write_report(run.path, manifest, audio_dir)


def _data(html):
    return json.loads(html.split("const DATA = ", 1)[1].split(";\nconst KEY", 1)[0])


def test_report_is_self_contained_and_blind(make_manifest, audio_dir, tmp_path):
    run, report = _report(make_manifest, audio_dir, tmp_path)
    html = report.read_text(encoding="utf-8")

    assert not re.search(r"<(script|link|img)[^>]+(src|href)=\"https?://", html)
    assert "fonts.googleapis" not in html
    assert run.run_id in html
    for artist in ("Broadcast", "Stereolab", "Portishead"):
        assert artist in html
    data = _data(html)
    assert data["models"] == ["hash", "hash2"]  # the unloadable model is left out
    assert all(s["audio"].startswith("file:///") for s in data["seeds"])
    broadcast = next(s for s in data["seeds"] if s["artist"] == "Broadcast")
    assert len(broadcast["neighbours"]["hash"]) == 2  # the other two seeds, never itself
    assert broadcast["start"] == round(12 * 0.35, 1)  # clips start partway in
    for duel in data["duels"]:
        assert {duel["l"], duel["r"]} == {0, 1}
        assert "hash" not in json.dumps(duel)  # duel data names no model
    metrics = json.loads((run.path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["models"]["hash"]["recall_seeds"] == 1
    assert set(metrics["overlap"]) == {"hash|hash2"}
    assert metrics == data["metrics"]


def test_rendering_twice_gives_the_same_duels(make_manifest, audio_dir, tmp_path):
    run, report = _report(make_manifest, audio_dir, tmp_path)
    first = _data(report.read_text(encoding="utf-8"))["duels"]
    again = write_report(run.path, tmp_path / "manifest.csv", audio_dir)
    assert _data(again.read_text(encoding="utf-8"))["duels"] == first


def _votes(path, run_id, entries):
    path.write_text(json.dumps({"run_id": run_id, "votes": entries}), encoding="utf-8")
    return path


def _vote(a, b, winner):
    return {"seed": "s", "a": a, "b": b, "winner": winner}


def test_scoring_counts_wins_losses_and_ties(tmp_path):
    entries = (
        [_vote("muq", "mert", "muq")] * 4
        + [_vote("clap", "muq", "muq")] * 2
        + [_vote("muq", "mert", "mert")] * 2
        + [_vote("muq", "clap", "tie")] * 2
    )
    result = score(_votes(tmp_path / "v.json", "run-1", entries), "run-1", {"muq", "mert", "clap"})

    assert result["models"]["muq"] == {"wins": 6, "losses": 2, "ties": 2, "win_rate": 0.7}
    assert result["pairs"]["mert|muq"] == {"mert": 2, "muq": 4, "tie": 0}
    assert result["pairs"]["clap|muq"] == {"clap": 0, "muq": 2, "tie": 2}


def test_scoring_refuses_unknown_models(tmp_path):
    votes = _votes(tmp_path / "v.json", "run-1", [_vote("muq", "openl3", "muq")])
    with pytest.raises(VoteError, match="openl3"):
        score(votes, "run-1", {"muq", "mert"})


def test_scoring_refuses_another_runs_votes(make_manifest, audio_dir, tmp_path, capsys):
    run, _ = _report(make_manifest, audio_dir, tmp_path)
    votes = _votes(tmp_path / "v.json", "20990101-000000-other", [])

    assert main(["score", str(run.path), "--votes", str(votes)]) == 1
    err = capsys.readouterr().err
    assert "20990101-000000-other" in err and run.run_id in err


def test_score_cli_writes_scores(make_manifest, audio_dir, tmp_path):
    run, _ = _report(make_manifest, audio_dir, tmp_path)
    votes = _votes(tmp_path / "v.json", run.run_id, [_vote("hash", "hash2", "hash")])
    assert main(["score", str(run.path), "--votes", str(votes)]) == 0
    scores = json.loads((run.path / "scores.json").read_text())
    assert scores["models"]["hash"]["win_rate"] == 1.0
    assert scores["models"]["hash2"]["win_rate"] == 0.0
