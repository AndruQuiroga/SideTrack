"""Read the audio manifest exported by ``python -m sidetrack.audio manifest``."""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

COLUMNS = (
    "path",
    "sha256",
    "kind",
    "source",
    "source_id",
    "duration_s",
    "verification",
    "track_id",
    "artist",
    "title",
)
KINDS = {"full", "preview"}


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Asset:
    path: str
    sha256: str
    kind: str
    source: str
    source_id: str
    duration_s: float | None
    verification: str
    track_id: str | None
    artist: str
    title: str

    @property
    def seed(self) -> str:
        """One key per requested track: full and preview assets of a seed share it."""

        return self.track_id or f"{_norm(self.artist)}|{_norm(self.title)}"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def read_manifest(path: Path) -> list[Asset]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ManifestError(f"manifest is missing columns: {', '.join(sorted(missing))}")
        assets = []
        for line, row in enumerate(reader, start=2):
            if row["kind"] not in KINDS:
                raise ManifestError(f"line {line}: kind must be full or preview")
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ManifestError(f"line {line}: sha256 is not a hex digest")
            assets.append(
                Asset(
                    path=row["path"],
                    sha256=row["sha256"],
                    kind=row["kind"],
                    source=row["source"],
                    source_id=row["source_id"],
                    duration_s=float(row["duration_s"]) if row["duration_s"] else None,
                    verification=row["verification"],
                    track_id=row["track_id"] or None,
                    artist=row["artist"],
                    title=row["title"],
                )
            )
    return assets


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
