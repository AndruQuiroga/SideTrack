"""Spec: analysis/sound-dimensions: the blind review page and its decision file."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import pytest
from conftest import tone, write_wav
from test_dimensions import planted, write_manifest, write_run

from audio_lab.cli import main
from audio_lab.dimensions import DimensionsError, run_dimensions
from audio_lab.dimensions_review import ends_swapped, validate_decision, write_review
from audio_lab.seeds import OutputInRepo, repo_root

TRACKS = 150
SECRET = "zorptone"


@pytest.fixture()
def reviewed(tmp_path):
    """A dimensions run over synthetic tracks, with suggested names, and the audio to match."""

    x, basis = planted(np.random.default_rng(3), tracks=TRACKS, dim=16, strengths=(8.0, 5.0))
    run = write_run(tmp_path / "run", x)
    manifest = write_manifest(
        tmp_path / "manifest.csv",
        [(i, f"Artist {i}", f"Title {i}", "full", 200) for i in range(TRACKS)],
    )
    audio = tmp_path / "audio"
    audio.mkdir()
    for i in range(TRACKS):
        write_wav(audio / f"{i}.wav", tone(0.05, 220.0 + i))
    vocabulary = tmp_path / "vocabulary.csv"
    vocabulary.write_text(f"term\n{SECRET}\nplain\n", encoding="utf-8")

    def encoder(terms):
        return np.stack([basis[0], np.ones(16)])

    out = tmp_path / "dimensions"
    report = run_dimensions(run, manifest, out, names=True, vocabulary=vocabulary, encoder=encoder)
    assert report["components_stable"] >= 1
    return out, manifest, audio, report


def _page(reviewed, tmp_path, name="review.html"):
    out, manifest, audio, _ = reviewed
    return write_review(out, manifest, audio, tmp_path / name).read_text(encoding="utf-8")


def test_page_has_no_scores_or_names(reviewed, tmp_path):
    out, _, _, report = reviewed
    html = _page(reviewed, tmp_path)

    assert SECRET in (out / "dimensions.json").read_text(encoding="utf-8")  # suggested, not shown
    for forbidden in (SECRET, "suggested", "no_confident_label", "variance", "valence", "arousal"):
        assert forbidden not in html
    with (out / "scores.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for column in (c for c in row if c.startswith(("pc", "axis"))):
                assert row[column] not in html
            assert row["title"] not in html and row["artist"] not in html
    data = json.loads(re.search(r'id="data" type="application/json">(.*?)</script>', html, re.S)[1])
    assert set(data) == {"run_id", "axes"}
    for axis in data["axes"]:
        assert set(axis) == {"id", "a", "b"}
        assert len(axis["a"]) == len(axis["b"]) == 10
        assert all(set(track) == {"audio"} for track in axis["a"] + axis["b"])
        assert all("#t=70.0" in track["audio"] for track in axis["a"])  # 35% of 200 s
    assert len(data["axes"]) == len(report["axes"])


def test_page_is_self_contained(reviewed, tmp_path):
    html = _page(reviewed, tmp_path)

    assert not re.search(r"https?://", html)
    assert "<link" not in html and not re.search(r"<script[^>]*\ssrc=", html)
    assert "@import" not in html and "url(" not in html
    assert html.count("<audio") == 0  # created by the page's script from local file URIs
    assert "file://" in html


def test_order_is_fixed_by_run(reviewed, tmp_path):
    first = _page(reviewed, tmp_path, "one.html")
    second = _page(reviewed, tmp_path, "two.html")

    assert first == second
    sides = {ends_swapped(f"run-{i}", 0, "axis1") for i in range(40)}
    assert sides == {True, False}
    assert ends_swapped("run-1", 0, "axis1") == ends_swapped("run-1", 0, "axis1")
    assert any(
        ends_swapped("run-1", s, "axis1") != ends_swapped("run-1", 0, "axis1") for s in range(1, 30)
    )


def test_decision_file_is_validated(reviewed, tmp_path, capsys):
    out, *_ = reviewed
    report = json.loads((out / "dimensions.json").read_text(encoding="utf-8"))
    ids = [axis["id"] for axis in report["axes"]]
    good = {
        "run_id": report["run_id"],
        "decided_at": "2026-11-01",
        "axes": {ids[0]: {"decision": "keep", "name": "bright", "merge_into": ""}},
    }
    for other in ids[1:]:
        good["axes"][other] = {"decision": "drop", "name": "", "merge_into": ""}

    assert validate_decision(good, report)["keep"] == [ids[0]]

    unknown = {**good, "axes": {**good["axes"], "axis99": {"decision": "drop"}}}
    with pytest.raises(DimensionsError, match="axis99"):
        validate_decision(unknown, report)
    unnamed = {**good, "axes": {**good["axes"], ids[0]: {"decision": "keep", "name": " "}}}
    with pytest.raises(DimensionsError, match=ids[0]):
        validate_decision(unnamed, report)
    with pytest.raises(DimensionsError, match=ids[0]):
        validate_decision({**good, "axes": {**good["axes"], ids[0]: {"decision": "merge"}}}, report)
    with pytest.raises(DimensionsError, match="run"):
        validate_decision({**good, "run_id": "other"}, report)

    path = tmp_path / "dimensions-decision.json"
    path.write_text(json.dumps(unknown), encoding="utf-8")
    assert main(["dimensions-decision", str(out), str(path)]) == 1
    assert "axis99" in capsys.readouterr().err
    path.write_text(json.dumps(good), encoding="utf-8")
    assert main(["dimensions-decision", str(out), str(path)]) == 0


def test_review_refused_in_repo(reviewed):
    out, manifest, audio, _ = reviewed
    page = repo_root(Path(__file__)) / "dimensions-review-test.html"

    with pytest.raises(OutputInRepo):
        write_review(out, manifest, audio, page)
    assert not page.exists()
