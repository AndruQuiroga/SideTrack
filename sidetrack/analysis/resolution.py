"""Which audio stands for a track, and how much of a user's listening that reaches (openspec
analysis/listen-audio-resolution). Read models: nothing here writes."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.analysis.embeddings import ENABLED, is_current
from sidetrack.analysis.embeddings.registry import EmbeddingModel, enabled_model
from sidetrack.analysis.models import AudioAsset, AudioEmbedding, TrackAudioLink
from sidetrack.types import AudioKind, AudioVerification

DEFAULT_MODEL = next(iter(ENABLED))

OK = "ok"
NO_AUDIO = "no_audio"
AMBIGUOUS = "ambiguous"
NO_EMBEDDING = "no_embedding"


@dataclass(frozen=True)
class TrackAudio:
    """The audio of one track. ``asset_id`` is set for ``ok`` and ``no_embedding``;
    ``candidates`` lists the assets of ambiguous links for ``ambiguous``."""

    status: str
    asset_id: UUID | None = None
    kind: str | None = None
    method: str | None = None
    confidence: float | None = None
    candidates: list[UUID] = field(default_factory=list)
    # Every linked asset has been pruned, so none can be embedded again.
    files_missing: bool = False


def _current_embeddings(db: Session, asset_ids: set[UUID], spec: EmbeddingModel) -> set[UUID]:
    if not asset_ids:
        return set()
    rows = db.scalars(
        select(AudioEmbedding).where(
            AudioEmbedding.asset_id.in_(asset_ids), AudioEmbedding.model == spec.name
        )
    )
    return {row.asset_id for row in rows if is_current(row, spec)}


def resolve_tracks(
    db: Session, track_ids: Iterable[UUID], model: str = DEFAULT_MODEL
) -> dict[UUID, TrackAudio]:
    """``audio_for_track`` for many tracks with two queries."""

    spec = enabled_model(model)
    wanted = set(track_ids)
    by_track: dict[UUID, list[tuple[TrackAudioLink, AudioAsset]]] = defaultdict(list)
    if wanted:
        rows = db.execute(
            select(TrackAudioLink, AudioAsset)
            .join(AudioAsset, AudioAsset.id == TrackAudioLink.asset_id)
            .where(TrackAudioLink.track_id.in_(wanted))
        )
        for link, asset in rows:
            by_track[link.track_id].append((link, asset))
    embedded = _current_embeddings(db, {a.id for rows in by_track.values() for _, a in rows}, spec)

    result: dict[UUID, TrackAudio] = {}
    for track_id in wanted:
        pairs = by_track.get(track_id, [])
        if not pairs:
            result[track_id] = TrackAudio(NO_AUDIO)
            continue
        settled = [(link, asset) for link, asset in pairs if not link.ambiguous]
        if not settled:
            candidates = sorted(asset.id for _, asset in pairs)
            result[track_id] = TrackAudio(AMBIGUOUS, candidates=candidates)
            continue
        # An embedded asset beats one without, then a full track beats a preview and a
        # confirmed asset an unverified one; ties go to confidence and the newest fetch.
        best_link, best = max(
            settled,
            key=lambda pair: (
                pair[1].id in embedded,
                pair[1].kind is AudioKind.FULL,
                pair[1].verification is AudioVerification.CONFIRMED,
                pair[0].confidence,
                pair[1].fetched_at,
                str(pair[1].id),
            ),
        )
        result[track_id] = TrackAudio(
            OK if best.id in embedded else NO_EMBEDDING,
            asset_id=best.id,
            kind=best.kind.value,
            method=best_link.method,
            confidence=best_link.confidence,
            files_missing=all(asset.file_deleted_at is not None for _, asset in settled),
        )
    return result


def audio_for_track(db: Session, track_id: UUID, model: str = DEFAULT_MODEL) -> TrackAudio:
    """The audio that represents a track.

    Statuses: ``ok`` (the preferred asset has a current embedding), ``no_audio`` (no linked
    asset), ``ambiguous`` (only ambiguous links; ``candidates`` lists them) and
    ``no_embedding`` (linked, but no linked asset has a current embedding; the preferred
    asset is still returned). Nothing is stored, so a new embedding or a pruned file
    changes the answer without a write.
    """

    return resolve_tracks(db, [track_id], model)[track_id]
