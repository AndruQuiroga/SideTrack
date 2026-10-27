"""Optional label and co-listening files, matched to manifest assets by artist and title."""

from __future__ import annotations

import csv
from pathlib import Path

from .manifest import Asset, _norm


def label_key(artist: str, title: str) -> str:
    """Manifest rows keep their seed's artist and title, so this matches across files."""

    return f"{_norm(artist)}|{_norm(title)}"


def seed_index(assets: list[Asset]) -> dict[str, str]:
    """Label key → the asset seed key the report and neighbours use."""

    return {label_key(a.artist, a.title): a.seed for a in assets}


def read_labels(path: Path, assets: list[Asset]) -> dict[str, set[str]]:
    """Asset seed → its labels; rows for tracks not in the run are ignored."""

    index = seed_index(assets)
    out: dict[str, set[str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            seed = index.get(label_key(row["artist"], row["title"]))
            if seed and row.get("label"):
                out.setdefault(seed, set()).add(row["label"])
    return out


def read_colisten(path: Path, assets: list[Asset]) -> list[tuple[str, str]]:
    """Co-listened pairs whose two tracks are both in the run, as asset seed keys."""

    index = seed_index(assets)
    pairs = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            a = index.get(label_key(row["artist_a"], row["title_a"]))
            b = index.get(label_key(row["artist_b"], row["title_b"]))
            if a and b and a != b:
                pairs.append((a, b))
    return pairs
