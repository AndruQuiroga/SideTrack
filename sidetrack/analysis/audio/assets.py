"""Public audio-asset operations: fetch a seed, export a manifest, prune old files."""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import IO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import AudioAsset
from sidetrack.types import AudioKind, AudioSource, AudioVerification

from .sources import Seed, Source, SourceError
from .store import store_file
from .verify import AcoustIdClient, verify

logger = logging.getLogger(__name__)

SEED_COLUMNS = ("artist", "title", "album", "youtube_id", "deezer_id")
MANIFEST_COLUMNS = (
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

TrackResolver = Callable[[Session, Seed], UUID | None]


@dataclass(frozen=True)
class AssetOutcome:
    asset_id: UUID
    source: AudioSource
    kind: AudioKind
    verification: AudioVerification
    already_stored: bool
    note: str | None = None


@dataclass
class SeedResult:
    seed: Seed
    assets: list[AssetOutcome] = field(default_factory=list)
    missing: list[tuple[AudioSource, str]] = field(default_factory=list)


def read_seeds(handle: IO[str]) -> list[Seed]:
    """Seeds from CSV with a header: artist, title, and optional album, youtube_id, deezer_id."""

    reader = csv.DictReader(handle)
    missing = {"artist", "title"} - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"seed CSV needs columns: {', '.join(sorted(missing))}")
    seeds = []
    for row in reader:
        values = {k: (row.get(k) or "").strip() or None for k in SEED_COLUMNS}
        if not values["artist"] or not values["title"]:
            continue
        seeds.append(Seed(**values))  # type: ignore[arg-type]
    return seeds


def resolve_catalog_track(db: Session, seed: Seed) -> UUID | None:
    """Link to an existing or newly resolved catalog track through catalog's public API."""

    from sidetrack.catalog import resolve_listen_track

    try:
        track = resolve_listen_track(
            db,
            track_name=seed.title,
            artist_name=seed.artist,
            album_name=seed.album,
            track_mbid=None,
        )
    except Exception:  # MusicBrainz outages must not stop a fetch run
        logger.warning("Catalog resolution failed for %s - %s", seed.artist, seed.title)
        return None
    return track.id if track is not None else None


def fetch_seed(
    db: Session,
    seed: Seed,
    *,
    audio_dir: Path,
    sources: Iterable[Source],
    verifier: AcoustIdClient | None,
    resolve_track: TrackResolver = resolve_catalog_track,
) -> SeedResult:
    """Fetch every source for one seed, store and verify each file, and record assets.

    The caller commits. A source with no result or an error is recorded in ``missing``.
    """

    result = SeedResult(seed)
    track_id: UUID | None = None
    resolved = False
    for source in sources:
        try:
            download = source.fetch(seed, audio_dir)
        except SourceError as exc:
            result.missing.append((source.source, str(exc)))
            continue
        if download is None:
            result.missing.append((source.source, "no result"))
            continue

        stored = store_file(audio_dir, download.path, download.ext)
        existing = db.scalar(select(AudioAsset).where(AudioAsset.sha256 == stored.sha256))
        if existing is None:
            existing = db.scalar(
                select(AudioAsset).where(
                    AudioAsset.source == source.source,
                    AudioAsset.source_ref == download.source_ref,
                )
            )
            if existing is not None and not stored.existed:
                # Same upload, different bytes this time: keep the recorded file.
                (audio_dir / stored.path).unlink(missing_ok=True)
        if existing is not None:
            result.assets.append(
                AssetOutcome(existing.id, source.source, source.kind, existing.verification, True)
            )
            continue

        if not resolved:
            track_id, resolved = resolve_track(db, seed), True
        check = verify(verifier, audio_dir / stored.path, seed.artist, seed.title)
        asset = AudioAsset(
            sha256=stored.sha256,
            track_id=track_id,
            seed_artist=seed.artist,
            seed_title=seed.title,
            source=source.source,
            source_ref=download.source_ref,
            kind=source.kind,
            path=stored.path,
            format=download.ext.lower(),
            duration_s=check.duration_s,
            verification=check.status,
            acoustid_score=check.score,
            recording_mbid=check.recording_mbid,
            fetched_at=datetime.now(UTC),
        )
        db.add(asset)
        db.flush()
        result.assets.append(
            AssetOutcome(asset.id, source.source, source.kind, check.status, False, check.note)
        )
    return result


def export_manifest(db: Session, audio_dir: Path, out: IO[str]) -> int:
    """Write one CSV row per asset whose file still exists; return the row count."""

    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(MANIFEST_COLUMNS)
    rows = 0
    assets = db.scalars(
        select(AudioAsset)
        .where(AudioAsset.file_deleted_at.is_(None))
        .order_by(AudioAsset.seed_artist, AudioAsset.seed_title, AudioAsset.kind)
    )
    for asset in assets:
        if not (audio_dir / asset.path).is_file():
            continue
        writer.writerow(
            [
                asset.path,
                asset.sha256,
                asset.kind.value,
                asset.source.value,
                asset.source_ref,
                "" if asset.duration_s is None else f"{asset.duration_s:.2f}",
                asset.verification.value,
                asset.track_id or "",
                asset.seed_artist,
                asset.seed_title,
            ]
        )
        rows += 1
    return rows


def prune_assets(
    db: Session, audio_dir: Path, retention_days: int, now: datetime | None = None
) -> int:
    """Delete files older than the retention period; keep rows with a deletion time."""

    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=retention_days)
    expired = db.scalars(
        select(AudioAsset).where(
            AudioAsset.fetched_at < cutoff, AudioAsset.file_deleted_at.is_(None)
        )
    ).all()
    for asset in expired:
        (audio_dir / asset.path).unlink(missing_ok=True)
        asset.file_deleted_at = now
    db.flush()
    return len(expired)
