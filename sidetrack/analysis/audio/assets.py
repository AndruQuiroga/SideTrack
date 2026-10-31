"""Public audio-asset operations: fetch a seed, export or import a manifest, prune old files."""

from __future__ import annotations

import csv
import logging
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import IO, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import AudioAsset
from sidetrack.types import AudioKind, AudioSource, AudioVerification

from .sources import Seed, Source, SourceError
from .store import sha256_of, store_file
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
    "acoustid_score",
    "recording_mbid",
)
# Manifests exported before these columns existed still import.
_OPTIONAL_MANIFEST_COLUMNS = {"acoustid_score", "recording_mbid"}

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
                "" if asset.acoustid_score is None else asset.acoustid_score,
                asset.recording_mbid or "",
            ]
        )
        rows += 1
    return rows


@dataclass(frozen=True)
class ManifestIssue:
    path: str  # as written in the manifest, relative to the audio directory
    reason: str


@dataclass
class ManifestImportPlan:
    new: list[dict[str, Any]] = field(default_factory=list)  # AudioAsset values
    existing: int = 0
    rejected: list[ManifestIssue] = field(default_factory=list)
    conflicts: list[ManifestIssue] = field(default_factory=list)


def read_manifest(handle: IO[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(handle)
    required = set(MANIFEST_COLUMNS) - _OPTIONAL_MANIFEST_COLUMNS
    missing = required - set(reader.fieldnames or ())
    if missing:
        raise ValueError(f"Manifest is missing columns: {', '.join(sorted(missing))}")
    return list(reader)


def _manifest_values(row: dict[str, str]) -> dict[str, Any]:
    """AudioAsset values for one row; never the row's track link, which is another database's."""

    score = row.get("acoustid_score") or None
    return {
        "sha256": row["sha256"],
        "seed_artist": row["artist"],
        "seed_title": row["title"],
        "source": AudioSource(row["source"]),
        "source_ref": row["source_id"],
        "kind": AudioKind(row["kind"]),
        "path": row["path"],
        "format": PurePosixPath(row["path"]).suffix.removeprefix(".").lower(),
        "duration_s": float(row["duration_s"]) if row["duration_s"] else None,
        "verification": AudioVerification(row["verification"]),
        "acoustid_score": None if score is None else float(score),
        "recording_mbid": row.get("recording_mbid") or None,
    }


def _rejection(values: dict[str, Any], audio_dir: Path) -> str | None:
    relative = PurePosixPath(values["path"])
    if values["verification"] is AudioVerification.MISMATCH:
        return "verification is mismatch"
    if relative.is_absolute() or len(relative.parts) != 1 or relative.stem != values["sha256"]:
        return "file name does not match its hash"
    if not values["seed_artist"] or not values["seed_title"] or not values["source_ref"]:
        return "missing artist, title or source id"
    file = audio_dir / relative.name
    if not file.is_file():
        return "file is missing"
    if sha256_of(file) != values["sha256"]:
        return "file does not match its hash"
    return None


def plan_manifest_import(
    db: Session, audio_dir: Path, rows: Iterable[dict[str, str]]
) -> ManifestImportPlan:
    """Sort rows into new, existing, rejected and conflicting. Writes nothing."""

    plan = ManifestImportPlan()
    known = db.execute(select(AudioAsset.sha256, AudioAsset.source, AudioAsset.source_ref)).all()
    by_hash = {sha256: (source, ref) for sha256, source, ref in known}
    by_source = {(source, ref): sha256 for sha256, source, ref in known}
    for row in rows:
        path = row["path"]
        try:
            values = _manifest_values(row)
        except ValueError:
            plan.rejected.append(ManifestIssue(path, "row has an invalid value"))
            continue
        sha256, identity = values["sha256"], (values["source"], values["source_ref"])
        if by_hash.get(sha256, identity) != identity:
            plan.conflicts.append(ManifestIssue(path, "hash belongs to another source"))
        elif by_source.get(identity, sha256) != sha256:
            plan.conflicts.append(ManifestIssue(path, "source belongs to another hash"))
        elif sha256 in by_hash:
            plan.existing += 1
        elif (reason := _rejection(values, audio_dir)) is not None:
            plan.rejected.append(ManifestIssue(path, reason))
        else:
            plan.new.append(values)
            by_hash[sha256] = identity
            by_source[identity] = sha256
    return plan


def apply_manifest_import(db: Session, plan: ManifestImportPlan) -> int:
    """Add the plan's new assets to the caller's transaction; return how many."""

    now = datetime.now(UTC)  # so retention can't delete files on the day they arrive
    db.add_all(AudioAsset(fetched_at=now, **values) for values in plan.new)
    db.flush()
    return len(plan.new)


@dataclass
class ReverifyResult:
    counts: Counter = field(default_factory=Counter)  # verification -> assets
    reasons: Counter = field(default_factory=Counter)  # why assets stayed unverified


def reverify_assets(
    db: Session, audio_dir: Path, verifier: AcoustIdClient | None
) -> ReverifyResult:
    """Re-check ``unverified`` assets whose file exists; return new counts and reasons."""

    result = ReverifyResult()
    assets = db.scalars(
        select(AudioAsset).where(
            AudioAsset.verification == AudioVerification.UNVERIFIED,
            AudioAsset.file_deleted_at.is_(None),
        )
    ).all()
    for asset in assets:
        path = audio_dir / asset.path
        if not path.is_file():
            continue
        check = verify(verifier, path, asset.seed_artist, asset.seed_title)
        asset.verification = check.status
        asset.acoustid_score = check.score
        asset.recording_mbid = check.recording_mbid
        asset.duration_s = check.duration_s or asset.duration_s
        result.counts[check.status] += 1
        if check.status is AudioVerification.UNVERIFIED and check.note:
            result.reasons[check.note] += 1
    db.flush()
    return result


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
