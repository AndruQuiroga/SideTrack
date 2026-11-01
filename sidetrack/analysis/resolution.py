"""Which audio stands for a track, and how much of a user's listening that reaches (openspec
analysis/listen-audio-resolution). Read models: nothing here writes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from sidetrack.analysis.embeddings import ENABLED, is_current
from sidetrack.analysis.embeddings.registry import EmbeddingModel, enabled_model
from sidetrack.analysis.models import AudioAsset, AudioEmbedding, TrackAudioLink
from sidetrack.listening import ListenEvent, ListenSession, ListenSessionOverride
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


REASONS = ("no_link", "ambiguous", "no_embedding", "file_missing")
# Effective session classifications whose plays are not chosen listening. `unclassified`,
# `unknown` and a `keep` review count as included.
AUTOPLAY = frozenset({"night_autoplay", "autoplay"})


@dataclass
class Coverage:
    """Exact counts. Shares come from them, never the other way round."""

    start: datetime
    end: datetime
    model: str
    plays: int = 0
    covered: int = 0
    included_plays: int = 0
    covered_included: int = 0
    reasons: Counter[str] = field(default_factory=Counter)
    reasons_included: Counter[str] = field(default_factory=Counter)

    @staticmethod
    def share(part: int, whole: int) -> float | None:
        """None when there are no plays: no share is invented."""

        return part / whole if whole else None

    @property
    def share_all(self) -> float | None:
        return self.share(self.covered, self.plays)

    @property
    def share_included(self) -> float | None:
        return self.share(self.covered_included, self.included_plays)


def _reason(audio: TrackAudio) -> str:
    if audio.status == NO_AUDIO:
        return "no_link"
    if audio.status == AMBIGUOUS:
        return "ambiguous"
    return "file_missing" if audio.files_missing else "no_embedding"


def audio_coverage(
    db: Session, user_id: UUID, start: datetime, end: datetime, model: str = DEFAULT_MODEL
) -> Coverage:
    """What share of a user's plays in ``[start, end)`` resolve to an embedded asset.

    Counts all plays and the included ones (effective session classification not autoplay,
    where a ``keep`` review overrides the rule's flag), and buckets the rest by reason:
    ``no_link``, ``ambiguous``, ``no_embedding`` and ``file_missing`` (every linked asset
    has been pruned). Every figure derived from audio should print this.
    """

    enabled_model(model)
    plays = db.execute(
        select(
            ListenEvent.track_id,
            ListenSession.kind,
            ListenSessionOverride.override,
            func.count(),
        )
        .select_from(ListenEvent)
        .outerjoin(ListenSession, ListenSession.id == ListenEvent.session_id)
        .outerjoin(
            ListenSessionOverride,
            and_(
                ListenSessionOverride.user_id == ListenSession.user_id,
                ListenSessionOverride.started_at == ListenSession.started_at,
                ListenSessionOverride.ended_at == ListenSession.ended_at,
            ),
        )
        .where(
            ListenEvent.user_id == user_id,
            ListenEvent.played_at >= start,
            ListenEvent.played_at < end,
        )
        .group_by(ListenEvent.track_id, ListenSession.kind, ListenSessionOverride.override)
    ).all()
    audio = resolve_tracks(db, {row[0] for row in plays}, model)
    report = Coverage(start=start, end=end, model=model)
    for track_id, kind, override, count in plays:
        included = (override or kind) not in AUTOPLAY
        resolved = audio[track_id]
        report.plays += count
        report.included_plays += count if included else 0
        if resolved.status == OK:
            report.covered += count
            report.covered_included += count if included else 0
            continue
        report.reasons[_reason(resolved)] += count
        if included:
            report.reasons_included[_reason(resolved)] += count
    return report
