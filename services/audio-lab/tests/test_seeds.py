"""Spec: analysis/benchmark-seeds, personal seeds from a synthetic ListenBrainz export."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from audio_lab.cli import main
from audio_lab.seeds import (
    Options,
    OutputInRepo,
    build_seeds,
    colisten_pairs,
    is_night,
    read_export,
    repo_root,
    resolve,
    sessions,
)

DAY = datetime(2024, 5, 1, 12, 0, tzinfo=UTC).timestamp()
NIGHT = datetime(2024, 5, 1, 23, 0, tzinfo=UTC).timestamp()


def listen(at, artist, title, *, duration_ms=None, mbid=None, mapped=None, video=None):
    info = {}
    if duration_ms:
        info["duration_ms"] = duration_ms
    if video:
        info["origin_url"] = f"https://music.youtube.com/watch?v={video}"
    md = {"artist_name": artist, "track_name": title, "additional_info": info}
    if mbid:
        md["mbid_mapping"] = {
            "recording_mbid": mbid,
            "recording_name": mapped[1],
            "artists": [{"artist_credit_name": mapped[0], "join_phrase": ""}],
        }
    return {"listened_at": at, "track_metadata": md}


def write_export(root, listens, loved=()):
    for item in listens:
        year = datetime.fromtimestamp(item["listened_at"], UTC).year
        folder = root / "listens" / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "1.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item) + "\n")
    (root / "feedback.jsonl").write_text(
        "".join(json.dumps({"score": 1, "recording_mbid": m}) + "\n" for m in loved), "utf-8"
    )
    return root


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# Personal seeds exclude non-music


def test_podcast_and_pseudo_artist_excluded(tmp_path):
    export = write_export(
        tmp_path / "lb",
        [
            listen(DAY, "Guess the Character", "The Best in Jest", duration_ms=3_300_000),
            listen(DAY + 60, "A YouTube Labs experiment", "Mix"),
            listen(DAY + 120, "Some Show", "Episode 12"),
            listen(DAY + 180, "Dabin", "Alive"),
        ],
    )
    listens, _, excluded = read_export(export)

    assert [x.artist for x in listens] == ["Dabin"]
    assert excluded == {"too_long": 1, "pseudo_artist": 1, "podcast": 1}


# Uploader-channel listens resolve to the real artist


def test_channel_upload_resolves():
    assert resolve({"artist_name": "AirwaveMusicTV", "track_name": "Dabin - Alive"}) == (
        "Dabin",
        "Alive",
    )
    assert resolve(
        {"artist_name": "MrSuicideSheep", "track_name": "Seven Lions - Polarized (Official Video)"}
    ) == ("Seven Lions", "Polarized")


def test_mapped_listen_keeps_mapping():
    md = listen(DAY, "Chan", "X - Y", mbid="m1", mapped=("Jason Ross", "One Time"))
    assert resolve(md["track_metadata"]) == ("Jason Ross", "One Time")


# Personal seeds are balanced; co-listening pairs are recorded; sleep is labelled


def _favourites(start, artist, count, plays=2):
    return [
        listen(start + i * 7200 + p * 86400, artist, f"Song {i}")
        for i in range(count)
        for p in range(plays)
    ]


def test_artist_cap_and_years(tmp_path):
    old = datetime(2020, 3, 1, 12, tzinfo=UTC).timestamp()
    new = datetime(2026, 3, 1, 12, tzinfo=UTC).timestamp()
    export = write_export(
        tmp_path / "lb",
        _favourites(old, "Illenium", 50)
        + _favourites(new, "Kasbo", 3)
        + _favourites(old, "Eden", 3),
    )
    out = tmp_path / "out"
    build_seeds(export, out, Options(count=6), tz=UTC)
    seeds = rows(out / "seeds.csv")

    by_artist = {}
    for s in seeds:
        by_artist[s["artist"]] = by_artist.get(s["artist"], 0) + 1
    assert by_artist == {"Illenium": 2, "Kasbo": 2, "Eden": 2}
    report = json.loads((out / "seeds-report.json").read_text())
    assert set(report["seeds_by_year"]) == {"2020", "2026"}


def test_deterministic(tmp_path):
    export = write_export(tmp_path / "lb", _favourites(DAY, "A", 5) + _favourites(DAY, "B", 5))
    build_seeds(export, tmp_path / "one", Options(count=4), tz=UTC)
    build_seeds(export, tmp_path / "two", Options(count=4), tz=UTC)
    for name in ("seeds.csv", "labels.csv", "colisten.csv"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()


def _pair_sessions(a, b, days, start=DAY):
    out = []
    for d in range(days):
        at = start + d * 86400
        out += [listen(at, *a), listen(at + 200, *b)]
    return out


def test_repeated_pair_recorded_and_one_off_not(tmp_path):
    listens = _pair_sessions(("A", "Up"), ("B", "Down"), 4)
    listens += [listen(DAY + 10 * 86400, "A", "Up"), listen(DAY + 10 * 86400 + 200, "C", "Once")]
    export = write_export(tmp_path / "lb", listens)
    out = tmp_path / "out"
    build_seeds(export, out, Options(count=10), tz=UTC)

    pairs = rows(out / "colisten.csv")
    assert [(p["artist_a"], p["artist_b"], p["sessions"]) for p in pairs] == [("A", "B", "4")]


def _night(start, tracks):
    """One night session: 12+ listens over more than an hour, starting at 23:00."""

    return [listen(start + i * 330, a, t) for i, (a, t) in enumerate(tracks)]


def test_night_autoplay_ignored_for_colistening(tmp_path):
    filler = [("Filler", f"F{i}") for i in range(10)]
    listens = []
    for d in range(5):
        listens += _night(NIGHT + d * 86400, [("A", "Up"), ("D", "Drift"), *filler])
    export = write_export(tmp_path / "lb", listens)
    listens_, _, _ = read_export(export)
    groups = sessions(listens_)

    night = {i for i, g in enumerate(groups) if is_night(g, UTC)}
    assert night == set(range(5))
    assert colisten_pairs(groups, night, 3) == {}


def test_sleep_labels(tmp_path):
    filler = [("Filler", f"F{i}") for i in range(11)]
    listens = []
    for d in range(3):
        listens += _night(NIGHT + d * 86400, [("Sleepy", "Rain"), *filler])
    # A daytime favourite heard twice at night: 10 plays, 2 in night sessions.
    for d in range(2):
        listens += _night(NIGHT + (10 + d) * 86400, [("Fav", "Hit"), *filler])
    listens += [listen(DAY + d * 86400, "Fav", "Hit") for d in range(20, 28)]
    export = write_export(tmp_path / "lb", listens)
    out = tmp_path / "out"
    build_seeds(export, out, Options(count=20, sleep_share=1.0), tz=UTC)

    labels = {(r["artist"], r["label"]) for r in rows(out / "labels.csv")}
    assert ("Sleepy", "sleep") in labels
    assert ("Fav", "personal") in labels


# Personal data stays outside the repo


def test_output_inside_repo_refused(tmp_path):
    export = write_export(tmp_path / "lb", [listen(DAY, "A", "B")])
    root = repo_root(Path(__file__).resolve())
    assert root is not None
    target = root / "build" / "personal-seeds-test"

    with pytest.raises(OutputInRepo):
        build_seeds(export, target, Options())
    assert not target.exists()
    assert main(["seeds", str(export), "--out", str(target)]) == 1
    assert not target.exists()


def test_sleep_share_is_filled_even_when_rarely_played(tmp_path):
    filler = [("Filler", f"F{i}") for i in range(11)]
    listens = []
    for d in range(2):
        listens += _night(NIGHT + d * 86400, [("Sleepy", "Rain"), *filler])
    listens += _favourites(DAY + 30 * 86400, "Loud", 1, plays=9)
    listens += [x for i in range(10) for x in _favourites(DAY + 40 * 86400, f"Band{i}", 1, plays=5)]
    export = write_export(tmp_path / "lb", listens)
    out = tmp_path / "out"
    build_seeds(export, out, Options(count=10, sleep_share=0.1, colisten_share=0), tz=UTC)

    labels = rows(out / "labels.csv")
    assert sum(r["label"] == "sleep" for r in labels) == 1
