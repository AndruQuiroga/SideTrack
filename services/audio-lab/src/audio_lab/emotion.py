"""Turn a local emotion dataset into an ordinary manifest plus mood labels.

The dataset and everything written from it stay outside the repo.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from .manifest import COLUMNS, file_sha256
from .seeds import ensure_outside_repo

AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
LABEL_COLUMNS = ("sha256", "valence", "arousal", "group")
MANIFEST = "manifest.csv"
LABELS = "mood-labels.csv"
REPORT = "emotion-report.json"


class EmotionDataError(ValueError):
    pass


@dataclass(frozen=True)
class Scale:
    low: float = 1.0
    high: float = 9.0

    def rescale(self, value: float) -> float:
        """Map the rating scale onto -1 to 1."""

        middle = (self.low + self.high) / 2
        return (value - middle) / ((self.high - self.low) / 2)


def _rows(path: Path) -> list[dict[str, str]]:
    """CSV rows with cleaned-up headers; released annotation files pad theirs with spaces."""

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return [{(k or "").strip().casefold(): (v or "").strip() for k, v in r.items()} for r in rows]


def _ratings(path: Path, scale: Scale) -> tuple[dict[str, tuple[float, float]], int]:
    rows = _rows(path)
    if rows and not {"song_id", "valence_mean", "arousal_mean"} <= rows[0].keys():
        raise EmotionDataError(f"{path.name} needs song_id, valence_mean and arousal_mean")
    ratings, unusable = {}, 0
    for row in rows:
        try:
            valence, arousal = float(row["valence_mean"]), float(row["arousal_mean"])
        except ValueError:
            unusable += 1
            continue
        ratings[row["song_id"]] = (scale.rescale(valence), scale.rescale(arousal))
    return ratings, unusable


def _artists(paths: list[Path]) -> dict[str, str]:
    artists = {}
    for path in paths:
        for row in _rows(path):
            if row.get("song_id") and row.get("artist"):
                artists[row["song_id"]] = row["artist"]
    return artists


def prepare_dataset(
    ratings_path: Path,
    audio_dir: Path,
    out: Path,
    *,
    metadata: list[Path] | None = None,
    scale: Scale | None = None,
    source: str = "deam",
) -> dict:
    """Write manifest.csv, mood-labels.csv and emotion-report.json into `out`."""

    ensure_outside_repo(out)
    ratings, unusable = _ratings(ratings_path, scale or Scale())
    artists = _artists(metadata or [])
    audio = {p.stem: p for p in audio_dir.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES}

    manifest, labels = [], []
    for clip in sorted(ratings.keys() & audio.keys(), key=lambda value: (len(value), value)):
        file = audio[clip]
        sha256 = file_sha256(file)
        artist = artists.get(clip)
        manifest.append(
            {
                "path": file.name,
                "sha256": sha256,
                "kind": "full",
                "source": source,
                "source_id": clip,
                "duration_s": "",
                "verification": "unverified",
                "track_id": "",
                "artist": artist or source,
                "title": clip,
            }
        )
        valence, arousal = ratings[clip]
        # Without an artist, a clip can only be sure of being separate from itself.
        group = f"artist:{artist.casefold()}" if artist else f"clip:{clip}"
        labels.append({"sha256": sha256, "valence": valence, "arousal": arousal, "group": group})

    summary = {
        "clips": len(manifest),
        "rated_without_audio": len(ratings.keys() - audio.keys()),
        "audio_without_rating": len(audio.keys() - ratings.keys()),
        "unusable_ratings": unusable,
        "groups": len({row["group"] for row in labels}),
    }
    out.mkdir(parents=True, exist_ok=True)
    _write(out / MANIFEST, COLUMNS, manifest)
    _write(out / LABELS, LABEL_COLUMNS, labels)
    (out / REPORT).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _write(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
