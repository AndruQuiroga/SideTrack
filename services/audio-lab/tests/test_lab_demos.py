"""Spec: analysis/listening-lab: the three demos, built from synthetic listening."""

from __future__ import annotations

import csv
import json
import re

import numpy as np
import pytest
from lab_support import sha, write_axes, write_plays
from test_dimensions import write_run
from test_tangents import AWAY, HOME, cycle, flat, home_days, session

from audio_lab.cli import main
from audio_lab.lab.demos import explorer, signature, timeline
from audio_lab.lab.site import LabContext, Unavailable, build_site
from audio_lab.manifest import COLUMNS

TRACKS = 18


def positions():
    rng = np.random.default_rng(7)
    home = rng.normal(0, 0.3, (10, 2))
    away = rng.normal(0, 0.3, (5, 2)) + [0, 6]
    far = rng.normal(0, 0.3, (3, 2)) + [0, -6]
    return np.vstack([home, away, far])


def write_manifest(tmp_path, with_audio):
    """A manifest for every track; audio files exist only for the tracks in ``with_audio``."""

    audio = tmp_path / "audio"
    audio.mkdir(exist_ok=True)
    path = tmp_path / "manifest.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(COLUMNS)
        for i in range(TRACKS):
            writer.writerow(
                [f"{i}.wav", sha(i), "full", "test", f"r{i}", 200, "confirmed", ""]
                + [f"Artist {i}", f"Title {i}"]
            )
            if i in with_audio:
                (audio / f"{i}.wav").write_bytes(b"RIFF")
    return path, audio


@pytest.fixture()
def context(tmp_path):
    dims, decision = write_axes(
        tmp_path / "dims", positions(), names={"axis1": "Calm", "axis2": "Chaos"}
    )
    plays = flat(
        home_days(0, 40)
        + [session(40 + d, cycle(AWAY, 4, d)) for d in range(14)]
        + home_days(54, 10)
        # 40 quiet days, then listening resumes: a gap the timeline must mark.
        + home_days(54 + 10 + 40, 12)
    )
    snapshot = write_plays(tmp_path / "snapshot.csv", plays)
    manifest, audio = write_manifest(tmp_path, with_audio=set(AWAY) | {0, 1, 2})
    vectors = np.random.default_rng(3).normal(size=(TRACKS, 5)) + 0.5
    run = write_run(tmp_path / "run", vectors)
    return LabContext(
        snapshot=snapshot,
        dimensions_dir=dims,
        decision=decision,
        manifest=manifest,
        audio_dir=audio,
        run_dir=run,
    ), vectors


def test_timeline_data_has_every_preset(context):
    data = timeline.build(context[0])
    assert list(data["presets"]) == ["strict", "normal", "loose"]
    assert [p["threshold"] for p in data["presets"].values()] == [2.5, 2.0, 1.5]
    for preset in data["presets"].values():
        assert {"branches", "gaps", "skips"} <= set(preset)
    assert "working values" in data["note"]
    (branch,) = data["presets"]["normal"]["branches"]
    assert branch["axis_name"] == "Chaos"
    assert [a["name"] for a in data["axes"]] == ["Calm", "Chaos"]
    json.dumps(data, allow_nan=False)  # the page parses this as JSON


def test_gaps_are_marked(context, tmp_path):
    data = timeline.build(context[0])
    for preset in data["presets"].values():
        (gap,) = preset["gaps"]
        assert gap["days"] >= 30
    out = tmp_path / "lab"
    build_site(out, context[0])
    page = (out / "timeline.html").read_text(encoding="utf-8")
    assert "stroke-dasharray" in page and "gap, " in page  # the code that draws a gap


def test_tracks_play_from_file_uris(context):
    data = timeline.build(context[0])
    tracks = [t for b in data["presets"]["normal"]["branches"] for t in b["top_tracks"]]
    assert tracks and all(t["audio"].startswith("file://") for t in tracks)
    assert all(t["audio"].endswith(".wav") for t in tracks)
    # Without a manifest nothing is playable, and the builder says so rather than inventing a path.
    bare = LabContext(
        snapshot=context[0].snapshot,
        dimensions_dir=context[0].dimensions_dir,
        decision=context[0].decision,
    )
    unplayable = timeline.build(bare)["presets"]["normal"]["branches"][0]["top_tracks"]
    assert all(t["audio"] is None for t in unplayable)


CLAIM_WORDING = re.compile(
    r"\b(mood|moods|feel|feels|felt|feeling|because|caused|causes|reason you|life event|breakup|"
    r"grief|sad|happy|depress\w*|anxious|stress\w*|you were|you are|you must|you needed)\b",
    re.I,
)


def test_no_claim_wording(context, tmp_path):
    out = tmp_path / "lab"
    entries = build_site(out, context[0])
    assert [e["status"] for e in entries] == ["ready"] * 3
    pages = sorted(out.glob("*.html"))
    assert len(pages) == 4
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert not CLAIM_WORDING.search(text), (page.name, CLAIM_WORDING.search(text))
        assert not re.search(r"https?://|<link|<script[^>]*\ssrc=", text)
    timeline_page = (out / "timeline.html").read_text(encoding="utf-8")
    assert "estimates of changes in sound" in timeline_page


def years_context(tmp_path, base):
    """Plenty of listening in 2025, a few plays in 2026."""

    plays = flat(
        [session(-300 + d, cycle(HOME, 4, d)) for d in range(40)]
        + [session(5, [10, 11, 12, 13]), session(6, [10, 11, 12])]
    )
    snapshot = write_plays(tmp_path / "years.csv", plays)
    return LabContext(snapshot=snapshot, dimensions_dir=base.dimensions_dir, decision=base.decision)


def test_signature_by_year(context, tmp_path):
    data = signature.build(years_context(tmp_path, context[0]))
    assert [(y["year"], y["plays"], y["tracks"]) for y in data["years"]] == [
        (2025, 160, 10),
        (2026, 7, 4),
    ]
    assert [a["name"] for a in data["axes"]] == ["Calm", "Chaos"]
    quiet, away = data["years"]
    assert all(len(y["values"]) == 2 for y in data["years"])
    assert away["values"][1] > quiet["values"][1] + 1  # 2026 sits far along Chaos
    json.dumps(data, allow_nan=False)


def test_sparse_year_is_marked(context, tmp_path):
    data = signature.build(years_context(tmp_path, context[0]))
    assert [(y["year"], y["sparse"]) for y in data["years"]] == [(2025, False), (2026, True)]
    assert "fewer than 30 plays" in data["sparse_rule"]
    out = tmp_path / "lab"
    build_site(out, years_context(tmp_path, context[0]), [signature.demo()])
    assert "sparse" in (out / "signature.html").read_text(encoding="utf-8")


def test_neighbours_exclude_the_track_itself(context):
    ctx, vectors = context
    data = explorer.build(ctx)
    assert len(data["tracks"]) == TRACKS
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    for index, track in enumerate(data["tracks"]):
        ids = [n["track"] for n in track["neighbours"]]
        assert index not in ids and len(ids) == len(set(ids)) == 10
        cosines = [n["cosine"] for n in track["neighbours"]]
        assert cosines == sorted(cosines, reverse=True)
        others = [j for j in np.argsort(-(unit @ unit[index]), kind="stable") if j != index]
        assert ids == [int(j) for j in others[:10]]
    assert len(data["tracks"][0]["axes"]) == 2


def test_track_without_audio_shows_unavailable(context, tmp_path):
    ctx, _ = context
    data = explorer.build(ctx)
    audio = [t["audio"] for t in data["tracks"]]
    assert audio[0].startswith("file://") and audio[3] is None  # track 3 has no file
    assert data["tracks"][3]["artist"] == "Artist 3"
    out = tmp_path / "lab"
    build_site(out, ctx, [explorer.demo()])
    assert "audio unavailable" in (out / "explorer.html").read_text(encoding="utf-8")


def test_demos_report_unavailable_inputs(tmp_path):
    for demo in (timeline, signature, explorer):
        with pytest.raises(Unavailable):
            demo.build(LabContext())
    entries = build_site(tmp_path / "lab", LabContext())
    assert [e["status"] for e in entries] == ["unavailable"] * 3
    assert "listening snapshot" in entries[0]["reason"]
    assert "embedding run" in entries[2]["reason"]


def test_documented_build_command(context, tmp_path, capsys):
    """The README's `lab build` with every input flag, on synthetic data."""

    ctx, _ = context
    out = tmp_path / "site"
    argv = ["lab", "build", "--out", str(out)]
    for flag, value in (
        ("--snapshot", ctx.snapshot),
        ("--dimensions", ctx.dimensions_dir),
        ("--manifest", ctx.manifest),
        ("--audio-dir", ctx.audio_dir),
        ("--run-dir", ctx.run_dir),
    ):
        argv += [flag, str(value)]
    assert main(argv) == 0
    lines = capsys.readouterr().out
    assert "timeline: ready" in lines and "explorer: ready" in lines
    assert sorted(p.name for p in out.glob("*.html")) == [
        "explorer.html",
        "index.html",
        "signature.html",
        "timeline.html",
    ]
