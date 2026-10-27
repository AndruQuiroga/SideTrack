"""A genre-labelled control set from Deezer's public genre charts (no key, read-only)."""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .manifest import _norm
from .seeds import LABEL_COLUMNS, SEED_COLUMNS, _write

API = "https://api.deezer.com"
USER_AGENT = "sidetrack-audio-lab (+https://github.com/AndruQuiroga/SideTrack)"
DEFAULT_GENRES = (
    "Pop",
    "Rap/Hip Hop",
    "Rock",
    "Dance",
    "R&B",
    "Alternative",
    "Electro",
    "Folk",
    "Reggae",
    "Jazz",
    "Country",
    "Classical",
    "Metal",
    "Soul & Funk",
    "Blues",
)

Fetch = Callable[[str], dict]


class ControlUnavailable(RuntimeError):
    pass


def deezer_fetch(min_interval: float = 1.0) -> Fetch:
    last = [0.0]

    def fetch(path: str) -> dict:
        wait = last[0] + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        last[0] = time.monotonic()
        request = urllib.request.Request(API + path, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except OSError as exc:
            raise ControlUnavailable(f"Deezer request {path} failed: {exc}") from exc

    return fetch


def _checked(data: dict, path: str) -> dict:
    if "error" in data:
        raise ControlUnavailable(f"Deezer request {path} failed: {data['error']}")
    return data


def control_seeds(
    fetch: Fetch, per_genre: int = 10, genres: tuple[str, ...] = DEFAULT_GENRES
) -> tuple[list[dict], list[dict]]:
    """Seed and label rows: per genre, chart tracks not already used, one per artist."""

    available = {g["name"]: g["id"] for g in _checked(fetch("/genre"), "/genre")["data"]}
    seeds, labels, used = [], [], set()
    for name in genres:
        if name not in available or available[name] == 0:
            continue
        path = f"/chart/{available[name]}/tracks?limit=100"
        artists: set[str] = set()
        taken = 0
        for track in _checked(fetch(path), path).get("data", []):
            artist = (track.get("artist") or {}).get("name", "")
            key = f"{_norm(artist)}|{_norm(track.get('title', ''))}"
            if not artist or key in used or _norm(artist) in artists:
                continue
            used.add(key)
            artists.add(_norm(artist))
            seeds.append(
                {
                    "artist": artist,
                    "title": track["title"],
                    "album": (track.get("album") or {}).get("title", ""),
                    "deezer_id": str(track["id"]),
                }
            )
            labels.append({"artist": artist, "title": track["title"], "label": f"genre:{name}"})
            taken += 1
            if taken == per_genre:
                break
    return seeds, labels


def write_control(out: Path, fetch: Fetch, per_genre: int, genres: tuple[str, ...]) -> int:
    """Write control-seeds.csv and control-labels.csv; nothing at all if Deezer fails."""

    seeds, labels = control_seeds(fetch, per_genre, genres)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "control-seeds.csv", SEED_COLUMNS, seeds)
    _write(out / "control-labels.csv", LABEL_COLUMNS, labels)
    return len(seeds)
