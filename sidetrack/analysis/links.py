"""Link catalog tracks to audio assets from evidence already stored (openspec
analysis/listen-audio-resolution).

Deterministic matchers only: a shared recording MBID, a shared YouTube video ID, or the same
normalised artist and title. Nothing here fetches, embeds or guesses on a partial match, and
sonic similarity never creates a link. The caller owns the transaction.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import (
    AudioAsset,
    TrackAudioLink,
    TrackAudioLinkCorrection,
)
from sidetrack.catalog import Track
from sidetrack.listening import clean_title, track_video_ids
from sidetrack.types import AudioSource, AudioVerification

MATCHER_VERSION = "links-v1"
SEED_IDENTITY_CONFIDENCE = 0.9
_VERSION = re.compile(r"^links-v(\d+)$")


def _version(value: str) -> int:
    found = _VERSION.match(value)
    return int(found.group(1)) if found else 0


def norm(text: str) -> str:
    """Casefold, drop accents and punctuation. The same rules built the benchmark seeds
    (audio-lab ``_norm``)."""

    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def asset_key(artist: str, title: str) -> str | None:
    """The identity key of a seed. None when either side normalises to nothing."""

    a, t = norm(artist), norm(title)
    return f"{a}|{t}" if a and t else None


def track_key(artist: str, title: str) -> str | None:
    """The identity key of a catalog track, with upload noise removed like the import does."""

    return asset_key(artist, clean_title(title))


@dataclass(frozen=True)
class Candidate:
    method: str
    confidence: float
    evidence: dict[str, Any]
    ambiguous: bool = False


@dataclass
class LinkReport:
    matcher_version: str = MATCHER_VERSION
    created: Counter[str] = field(default_factory=Counter)
    updated: int = 0
    links: Counter[str] = field(default_factory=Counter)
    ambiguous: int = 0
    unlinked_assets: int = 0
    unlinked_tracks: int = 0
    rejected: list[tuple[UUID, UUID]] = field(default_factory=list)


def _candidates(db: Session, user_id: UUID | None) -> dict[tuple[UUID, UUID], Candidate]:
    """Every pair the evidence supports. A pair keeps the first, most trusted, method."""

    found: dict[tuple[UUID, UUID], Candidate] = {}

    def add(track_id: UUID, asset_id: UUID, candidate: Candidate) -> None:
        found.setdefault((track_id, asset_id), candidate)

    for asset_id, track_id in db.execute(
        select(AudioAsset.id, AudioAsset.track_id).where(AudioAsset.track_id.is_not(None))
    ):
        add(track_id, asset_id, Candidate("seed", 1.0, {"source": "acquisition"}))

    for asset_id, track_id, mbid in db.execute(
        select(AudioAsset.id, Track.id, AudioAsset.recording_mbid)
        .join(Track, Track.musicbrainz_id == AudioAsset.recording_mbid)
        .where(
            AudioAsset.verification == AudioVerification.CONFIRMED,
            AudioAsset.recording_mbid.is_not(None),
        )
        .order_by(AudioAsset.id, Track.id)
    ):
        add(track_id, asset_id, Candidate("recording_mbid", 1.0, {"recording_mbid": mbid}))

    tracks_by_video: dict[str, list[UUID]] = defaultdict(list)
    for track_id, video in track_video_ids(db, user_id):
        tracks_by_video[video].append(track_id)
    if tracks_by_video:
        for asset_id, video in db.execute(
            select(AudioAsset.id, AudioAsset.source_ref)
            .where(
                AudioAsset.source == AudioSource.YOUTUBE_MUSIC,
                AudioAsset.source_ref.in_(list(tracks_by_video)),
            )
            .order_by(AudioAsset.id)
        ):
            for track_id in tracks_by_video[video]:
                add(track_id, asset_id, Candidate("youtube_id", 1.0, {"youtube_id": video}))

    for pair, candidate in _seed_identity(db).items():
        found.setdefault(pair, candidate)
    return found


def _seed_identity(db: Session) -> dict[tuple[UUID, UUID], Candidate]:
    tracks_by_key: dict[str, list[UUID]] = defaultdict(list)
    for track_id, artist, title in db.execute(
        select(Track.id, Track.artist_name, Track.title).order_by(Track.id)
    ):
        key = track_key(artist, title)
        if key:
            tracks_by_key[key].append(track_id)
    keyed: list[tuple[UUID, str, Any]] = []
    for asset_id, artist, title, kind in db.execute(
        select(
            AudioAsset.id, AudioAsset.seed_artist, AudioAsset.seed_title, AudioAsset.kind
        ).order_by(AudioAsset.id)
    ):
        key = asset_key(artist, title)
        if key and key in tracks_by_key:
            keyed.append((asset_id, key, kind))
    assets_per_key_kind = Counter((key, kind) for _, key, kind in keyed)
    out: dict[tuple[UUID, UUID], Candidate] = {}
    for asset_id, key, kind in keyed:
        track_ids = tracks_by_key[key]
        ambiguous = len(track_ids) > 1 or assets_per_key_kind[(key, kind)] > 1
        for track_id in track_ids:
            out[(track_id, asset_id)] = Candidate(
                "seed_identity", SEED_IDENTITY_CONFIDENCE, {"key": key}, ambiguous
            )
    return out


def _rejections_and_confirmations(
    db: Session,
) -> tuple[set[tuple[UUID, UUID]], set[tuple[UUID, UUID]]]:
    rejected: set[tuple[UUID, UUID]] = set()
    confirmed: set[tuple[UUID, UUID]] = set()
    for row in db.scalars(select(TrackAudioLinkCorrection)):
        (rejected if row.action == "reject" else confirmed).add((row.track_id, row.asset_id))
    return rejected, confirmed


def link_audio(db: Session, user_id: UUID | None = None) -> LinkReport:
    """Run every matcher once. Idempotent; keeps manual links.

    ``user_id`` limits the YouTube evidence and the unlinked-track count to one user's
    listens. The caller commits.
    """

    report = LinkReport()
    rejected, confirmed = _rejections_and_confirmations(db)
    existing = {(row.track_id, row.asset_id): row for row in db.scalars(select(TrackAudioLink))}
    now = datetime.now(UTC)
    for pair, candidate in _candidates(db, user_id).items():
        if pair in rejected:
            report.rejected.append(pair)
            continue
        ambiguous = candidate.ambiguous and pair not in confirmed
        row = existing.get(pair)
        if row is None:
            db.add(
                TrackAudioLink(
                    track_id=pair[0],
                    asset_id=pair[1],
                    method=candidate.method,
                    confidence=candidate.confidence,
                    matcher_version=MATCHER_VERSION,
                    evidence=candidate.evidence,
                    ambiguous=ambiguous,
                    linked_at=now,
                )
            )
            report.created[candidate.method] += 1
        elif row.method != "manual" and _version(row.matcher_version) < _version(MATCHER_VERSION):
            row.method = candidate.method
            row.confidence = candidate.confidence
            row.matcher_version = MATCHER_VERSION
            row.evidence = candidate.evidence
            row.ambiguous = ambiguous
            row.linked_at = now
            report.updated += 1
        elif row.method == candidate.method == "seed_identity":
            # Ambiguity follows the catalog, which changes between runs of one version.
            row.ambiguous = ambiguous
    db.flush()
    _fill_counts(db, report, user_id)
    return report


def _fill_counts(db: Session, report: LinkReport, user_id: UUID | None) -> None:
    report.links = Counter()
    for method, count in db.execute(
        select(TrackAudioLink.method, func.count()).group_by(TrackAudioLink.method)
    ):
        report.links[method] = count
    report.ambiguous = (
        db.scalar(select(func.count()).select_from(TrackAudioLink).where(TrackAudioLink.ambiguous))
        or 0
    )
    linked_assets = select(TrackAudioLink.asset_id)
    report.unlinked_assets = (
        db.scalar(
            select(func.count()).select_from(AudioAsset).where(AudioAsset.id.not_in(linked_assets))
        )
        or 0
    )
    tracks = (
        select(func.count())
        .select_from(Track)
        .where(Track.id.not_in(select(TrackAudioLink.track_id)))
    )
    if user_id is not None:
        from sidetrack.listening import ListenEvent

        tracks = tracks.where(
            Track.id.in_(select(ListenEvent.track_id).where(ListenEvent.user_id == user_id))
        )
    report.unlinked_tracks = db.scalar(tracks) or 0


def link_manually(db: Session, track_id: UUID, asset_id: UUID) -> TrackAudioLink:
    """An operator's link: method ``manual``, confidence 1.0, kept by every matcher run.

    Overrides an earlier rejection of the same pair. The caller commits.
    """

    if db.get(Track, track_id) is None or db.get(AudioAsset, asset_id) is None:
        raise ValueError("track_or_asset_not_found")
    correction = db.get(TrackAudioLinkCorrection, (track_id, asset_id))
    if correction is not None and correction.action == "reject":
        db.delete(correction)
    row = db.scalar(
        select(TrackAudioLink).where(
            TrackAudioLink.track_id == track_id, TrackAudioLink.asset_id == asset_id
        )
    )
    values = {
        "method": "manual",
        "confidence": 1.0,
        "matcher_version": MATCHER_VERSION,
        "evidence": {"source": "operator"},
        "ambiguous": False,
        "linked_at": datetime.now(UTC),
    }
    if row is None:
        row = TrackAudioLink(track_id=track_id, asset_id=asset_id, **values)
        db.add(row)
    else:
        for name, value in values.items():
            setattr(row, name, value)
    db.flush()
    return row


def correct_link(
    db: Session, track_id: UUID, asset_id: UUID, action: str, note: str | None = None
) -> None:
    """Record an operator's verdict on a pair. The caller commits.

    ``reject`` removes the link and stops the matcher recreating it. ``confirm`` clears
    ``ambiguous`` now and on every later run. The latest verdict for a pair replaces the
    earlier one.
    """

    if action not in ("reject", "confirm"):
        raise ValueError("unknown_action")
    if db.get(Track, track_id) is None or db.get(AudioAsset, asset_id) is None:
        raise ValueError("track_or_asset_not_found")
    now = datetime.now(UTC)
    correction = db.get(TrackAudioLinkCorrection, (track_id, asset_id))
    if correction is None:
        db.add(
            TrackAudioLinkCorrection(
                track_id=track_id, asset_id=asset_id, action=action, note=note, created_at=now
            )
        )
    else:
        correction.action, correction.note, correction.created_at = action, note, now
    row = db.scalar(
        select(TrackAudioLink).where(
            TrackAudioLink.track_id == track_id, TrackAudioLink.asset_id == asset_id
        )
    )
    if row is not None:
        if action == "reject":
            db.delete(row)
        else:
            row.ambiguous = False
    db.flush()
