"""Benchmark seeds from the owner's ListenBrainz export: cleaned, balanced and labelled.

The export and everything written from it are personal data and stay outside the repo.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .manifest import _norm
from .metrics import CREDIT_SPLIT

MAX_DURATION_S = 600
SESSION_GAP_S = 30 * 60
PSEUDO_ARTISTS = {"a youtube labs experiment"}
PODCAST_PATTERNS = (r"\bbest in jest\b", r"\bpodcast\b", r"\bepisode\b", r"\bep\.?\s*\d+\b")
# Bracketed upload noise: "(Official Video)", "[Monstercat Release]", "(Lyrics)".
_UPLOAD_NOISE = re.compile(
    r"\s*[\(\[][^\)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|release|out now|"
    r"free download|hd|hq|4k)\b[^\)\]]*[\)\]]",
    re.IGNORECASE,
)

SEED_COLUMNS = ("artist", "title", "album", "youtube_id", "deezer_id")
LABEL_COLUMNS = ("artist", "title", "label")
COLISTEN_COLUMNS = ("artist_a", "title_a", "artist_b", "title_b", "sessions")


class OutputInRepo(ValueError):
    pass


@dataclass(frozen=True)
class Listen:
    at: float
    key: str
    artist: str
    title: str
    album: str
    youtube_id: str | None
    mbid: str | None


@dataclass
class Track:
    key: str
    artist: str
    title: str
    album: str
    first_year: int
    plays: int = 0
    night_plays: int = 0
    loved: bool = False
    videos: Counter = field(default_factory=Counter)

    @property
    def primary(self) -> str:
        return next((n for p in CREDIT_SPLIT.split(self.artist) if (n := _norm(p))), "")

    @property
    def youtube_id(self) -> str:
        return self.videos.most_common(1)[0][0] if self.videos else ""


@dataclass(frozen=True)
class Options:
    count: int = 250
    per_artist: int = 2
    colisten_share: float = 0.25
    sleep_share: float = 0.15
    min_sessions: int = 3
    exclude_patterns: tuple[str, ...] = ()


def clean_title(text: str) -> str:
    return " ".join(_UPLOAD_NOISE.sub("", text).split())


def _video_id(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc == "youtu.be":
        return parsed.path.strip("/") or None
    return (parse_qs(parsed.query).get("v") or [None])[0]


def _duration_s(info: dict) -> float | None:
    if info.get("duration_ms"):
        return float(info["duration_ms"]) / 1000
    if info.get("duration"):
        return float(info["duration"])
    return None


def resolve(md: dict) -> tuple[str, str]:
    """(artist, title): the MusicBrainz mapping, else "Artist - Title" uploads, else raw."""

    mapping = md.get("mbid_mapping") or {}
    if mapping.get("recording_mbid") and mapping.get("artists"):
        artist = "".join(
            a.get("artist_credit_name", "") + a.get("join_phrase", "") for a in mapping["artists"]
        )
        return artist.strip(), clean_title(mapping.get("recording_name") or md["track_name"])
    title = md.get("track_name") or ""
    if " - " in title:
        artist, _, rest = title.partition(" - ")
        return artist.strip(), clean_title(rest)
    return (md.get("artist_name") or "").strip(), clean_title(title)


def read_export(
    root: Path, patterns: tuple[str, ...] = ()
) -> tuple[list[Listen], set[str], Counter]:
    """Listens in time order with non-music removed, loved recording MBIDs, exclusion counts."""

    podcast = re.compile("|".join(PODCAST_PATTERNS + patterns), re.IGNORECASE)
    excluded: Counter = Counter()
    listens = []
    for path in sorted((root / "listens").rglob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            md = raw["track_metadata"]
            info = md.get("additional_info") or {}
            duration = _duration_s(info)
            if duration and duration > MAX_DURATION_S:
                excluded["too_long"] += 1
                continue
            if _norm(md.get("artist_name") or "") in PSEUDO_ARTISTS:
                excluded["pseudo_artist"] += 1
                continue
            if podcast.search(f"{md.get('artist_name') or ''} {md.get('track_name') or ''}"):
                excluded["podcast"] += 1
                continue
            artist, title = resolve(md)
            if not artist or not title:
                excluded["missing_metadata"] += 1
                continue
            mapping = md.get("mbid_mapping") or {}
            listens.append(
                Listen(
                    float(raw["listened_at"]),
                    f"{_norm(artist)}|{_norm(title)}",
                    artist,
                    title,
                    md.get("release_name") or "",
                    _video_id(info.get("origin_url")),
                    mapping.get("recording_mbid"),
                )
            )
    listens.sort(key=lambda listen: (listen.at, listen.key))
    loved = set()
    feedback = root / "feedback.jsonl"
    if feedback.exists():
        for line in feedback.read_text(encoding="utf-8").splitlines():
            if line.strip() and (item := json.loads(line)).get("score") == 1:
                loved.add(item.get("recording_mbid"))
    return listens, loved, excluded


def sessions(listens: list[Listen]) -> list[list[Listen]]:
    out: list[list[Listen]] = []
    for listen in listens:
        if out and listen.at - out[-1][-1].at <= SESSION_GAP_S:
            out[-1].append(listen)
        else:
            out.append([listen])
    return out


def is_night(session: list[Listen], tz: tzinfo | None = None) -> bool:
    """Starts 22:00-04:00 local, lasts an hour or more, 12+ listens: sleep-tab autoplay."""

    hour = datetime.fromtimestamp(session[0].at, tz).hour
    long_enough = session[-1].at - session[0].at >= 3600
    return (hour >= 22 or hour < 4) and long_enough and len(session) >= 12


def tracks_from(
    listens: list[Listen], loved: set[str], night: set[int], groups: list[list[Listen]], tz
) -> dict[str, Track]:
    tracks: dict[str, Track] = {}
    for index, group in enumerate(groups):
        for listen in group:
            track = tracks.get(listen.key)
            if track is None:
                year = datetime.fromtimestamp(listen.at, tz).year
                track = tracks[listen.key] = Track(
                    listen.key, listen.artist, listen.title, listen.album, year
                )
            track.plays += 1
            track.night_plays += index in night
            track.loved |= listen.mbid in loved
            if listen.youtube_id:
                track.videos[listen.youtube_id] += 1
    return tracks


def is_sleep(track: Track) -> bool:
    return track.night_plays >= 2 and track.night_plays / track.plays >= 0.75


def colisten_pairs(
    groups: list[list[Listen]], night: set[int], min_sessions: int
) -> dict[tuple[str, str], int]:
    """Adjacent pairs → number of distinct non-night sessions they occurred in."""

    seen: dict[tuple[str, str], set[int]] = defaultdict(set)
    for index, group in enumerate(groups):
        if index in night:
            continue
        for a, b in zip(group, group[1:], strict=False):
            if a.key != b.key:
                seen[tuple(sorted((a.key, b.key)))].add(index)  # type: ignore[index]
    return {pair: len(s) for pair, s in seen.items() if len(s) >= min_sessions}


def _band(plays: int) -> int:
    return 0 if plays <= 3 else 1 if plays <= 9 else 2


def select(
    tracks: dict[str, Track], pairs: dict[tuple[str, str], int], options: Options
) -> list[Track]:
    """Co-listened pairs first, then round-robin over (first year, play band) buckets."""

    eligible = {k: t for k, t in tracks.items() if t.loved or t.plays >= 2}
    chosen: list[Track] = []
    chosen_keys: set[str] = set()
    per_artist: Counter = Counter()
    sleep_cap = int(options.count * options.sleep_share)
    sleeping = 0

    def fits(batch: list[Track]) -> bool:
        need = Counter(t.primary for t in batch)
        sleep_need = sum(is_sleep(t) for t in batch)
        return (
            all(t.key not in chosen_keys for t in batch)
            and all(per_artist[a] + n <= options.per_artist for a, n in need.items())
            and sleeping + sleep_need <= sleep_cap
            and len(chosen) + len(batch) <= options.count
        )

    def take(batch: list[Track]) -> None:
        nonlocal sleeping
        for t in batch:
            chosen.append(t)
            chosen_keys.add(t.key)
            per_artist[t.primary] += 1
            sleeping += is_sleep(t)

    pair_target = int(options.count * options.colisten_share)
    for (a, b), _ in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
        if len(chosen) >= pair_target:
            break
        if a in eligible and b in eligible:
            batch = [t for t in (eligible[a], eligible[b]) if t.key not in chosen_keys]
            if batch and fits(batch):
                take(batch)

    # Sleep tracks are rarely replayed by choice, so the play-ordered buckets would never
    # reach them: fill the sleep share first, most night plays first.
    for t in sorted(
        (t for t in eligible.values() if is_sleep(t)), key=lambda t: (-t.night_plays, t.key)
    ):
        if sleeping >= sleep_cap:
            break
        if t.key not in chosen_keys and fits([t]):
            take([t])

    buckets: dict[tuple[int, int], list[Track]] = defaultdict(list)
    for t in eligible.values():
        buckets[(t.first_year, _band(t.plays))].append(t)
    queues = [
        sorted(buckets[key], key=lambda t: (not t.loved, -t.plays, t.key))
        for key in sorted(buckets)
    ]
    while len(chosen) < options.count and any(queues):
        for queue in queues:
            while queue:
                candidate = queue.pop(0)
                if fits([candidate]):
                    take([candidate])
                    break
            if len(chosen) >= options.count:
                break
    return chosen


def repo_root(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def ensure_outside_repo(out: Path) -> None:
    root = repo_root(Path(__file__).resolve().parent)
    target = out.resolve()
    if root is not None and (target == root or root in target.parents):
        raise OutputInRepo(f"{out} is inside the repository {root}; personal data stays outside")


def _write(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_seeds(export: Path, out: Path, options: Options, tz: tzinfo | None = None) -> dict:
    """Write seeds.csv, labels.csv, colisten.csv and seeds-report.json into ``out``."""

    ensure_outside_repo(out)
    listens, loved, excluded = read_export(export, options.exclude_patterns)
    groups = sessions(listens)
    night = {i for i, g in enumerate(groups) if is_night(g, tz)}
    tracks = tracks_from(listens, loved, night, groups, tz)
    pairs = colisten_pairs(groups, night, options.min_sessions)
    chosen = select(tracks, pairs, options)
    keys = {t.key for t in chosen}
    kept_pairs = {p: n for p, n in pairs.items() if p[0] in keys and p[1] in keys}

    out.mkdir(parents=True, exist_ok=True)
    _write(
        out / "seeds.csv",
        SEED_COLUMNS,
        [
            {"artist": t.artist, "title": t.title, "album": t.album, "youtube_id": t.youtube_id}
            for t in chosen
        ],
    )
    _write(
        out / "labels.csv",
        LABEL_COLUMNS,
        [
            {"artist": t.artist, "title": t.title, "label": "sleep" if is_sleep(t) else "personal"}
            for t in chosen
        ],
    )
    _write(
        out / "colisten.csv",
        COLISTEN_COLUMNS,
        [
            {
                "artist_a": tracks[a].artist,
                "title_a": tracks[a].title,
                "artist_b": tracks[b].artist,
                "title_b": tracks[b].title,
                "sessions": n,
            }
            for (a, b), n in sorted(kept_pairs.items())
        ],
    )
    report = {
        "listens_kept": len(listens),
        "excluded": dict(sorted(excluded.items())),
        "sessions": len(groups),
        "night_sessions": len(night),
        "tracks": len(tracks),
        "eligible": sum(1 for t in tracks.values() if t.loved or t.plays >= 2),
        "colisten_pairs": len(pairs),
        "seeds": len(chosen),
        "sleep_seeds": sum(is_sleep(t) for t in chosen),
        "seed_pairs": len(kept_pairs),
        "seeds_by_year": dict(sorted(Counter(t.first_year for t in chosen).items())),
    }
    (out / "seeds-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
