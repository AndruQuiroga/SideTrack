"""Spec: analysis/audio-benchmark: emotion datasets become ordinary benchmark inputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from audio_lab.cli import main
from audio_lab.emotion import EmotionDataError, Scale, prepare_dataset
from audio_lab.manifest import read_manifest
from audio_lab.seeds import OutputInRepo, repo_root

RATINGS = "song_id, valence_mean, valence_std, arousal_mean, arousal_std\n"


def _dataset(tmp_path: Path, ratings: dict[str, tuple[str, str]], audio: list[str]) -> tuple:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    for clip in audio:
        (audio_dir / f"{clip}.mp3").write_bytes(f"audio {clip}".encode())
    path = tmp_path / "ratings.csv"
    body = "".join(f"{c}, {v}, 1, {a}, 1\n" for c, (v, a) in ratings.items())
    path.write_text(RATINGS + body, "utf-8")
    return path, audio_dir


def _labels(out: Path) -> list[dict]:
    with (out / "mood-labels.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_prepares_three_clips(tmp_path):
    ratings = {"2": ("5", "5"), "3": ("1", "9"), "4": ("7", "3")}
    path, audio_dir = _dataset(tmp_path, ratings, ["2", "3", "4"])
    out = tmp_path / "out"

    summary = prepare_dataset([path], audio_dir, out)

    assert summary["clips"] == 3
    assets = read_manifest(out / "manifest.csv")
    assert [a.source_id for a in assets] == ["2", "3", "4"]
    assert {a.source for a in assets} == {"deam"}
    assert len(_labels(out)) == 3
    assert json.loads((out / "emotion-report.json").read_text("utf-8")) == summary


def test_rating_is_rescaled(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "1"), "3": ("9", "7")}, ["2", "3"])
    out = tmp_path / "out"

    prepare_dataset([path], audio_dir, out)

    rows = _labels(out)
    assert [(float(r["valence"]), float(r["arousal"])) for r in rows] == [(0, -1), (1, 0.5)]
    assert Scale(0, 10).rescale(5) == 0


def test_clip_without_audio_is_counted(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "5"), "3": ("5", "5")}, ["2", "9"])
    out = tmp_path / "out"

    summary = prepare_dataset([path], audio_dir, out)

    assert summary["clips"] == 1
    assert summary["rated_without_audio"] == 1
    assert summary["audio_without_rating"] == 1
    assert [a.source_id for a in read_manifest(out / "manifest.csv")] == ["2"]


def test_unusable_rating_is_not_filled_in(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("", "5"), "3": ("5", "5")}, ["2", "3"])
    out = tmp_path / "out"

    summary = prepare_dataset([path], audio_dir, out)

    assert summary["unusable_ratings"] == 1
    assert summary["clips"] == 1


def test_artist_metadata_groups_clips(tmp_path):
    path, audio_dir = _dataset(
        tmp_path, {"2": ("5", "5"), "3": ("5", "5"), "4": ("5", "5")}, ["2", "3", "4"]
    )
    metadata = tmp_path / "metadata.csv"
    metadata.write_text("song_id, Artist, Song title\n2, Band, A\n3, BAND, B\n", "utf-8")
    out = tmp_path / "out"

    summary = prepare_dataset([path], audio_dir, out, metadata=[metadata])

    assert summary["groups"] == 2
    assert [r["group"] for r in _labels(out)] == ["artist:band", "artist:band", "clip:4"]


def test_wrong_columns_are_refused(tmp_path):
    path = tmp_path / "ratings.csv"
    path.write_text("id,score\n1,2\n", "utf-8")
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    with pytest.raises(EmotionDataError, match="valence_mean"):
        prepare_dataset([path], audio_dir, tmp_path / "out")


def test_ratings_can_span_files(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "5")}, ["2", "2001"])
    second = tmp_path / "later.csv"
    second.write_text(
        "song_id, valence_mean, valence_std, valence_ max_mean, arousal_mean\n"
        "2001, 3.2, 0.98, 5.0, 7\n",
        "utf-8",
    )
    out = tmp_path / "out"

    summary = prepare_dataset([path, second], audio_dir, out)

    assert summary["clips"] == 2
    assert float(_labels(out)[1]["arousal"]) == 0.5


def test_song_rated_twice_is_refused(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "5")}, ["2"])

    with pytest.raises(EmotionDataError, match="rated twice"):
        prepare_dataset([path, path], audio_dir, tmp_path / "out")


def test_refuses_output_in_repo(tmp_path):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "5")}, ["2"])
    root = repo_root(Path(__file__).resolve().parent)
    assert root is not None

    with pytest.raises(OutputInRepo):
        prepare_dataset([path], audio_dir, root / "mood-output")

    assert not (root / "mood-output").exists()


def test_cli_prepares_a_dataset(tmp_path, capsys):
    path, audio_dir = _dataset(tmp_path, {"2": ("5", "5")}, ["2"])
    out = tmp_path / "out"

    args = ["emotion-manifest", "--ratings", str(path), "--audio-dir", str(audio_dir)]
    code = main([*args, "--out", str(out)])

    assert code == 0
    assert '"clips": 1' in capsys.readouterr().out
