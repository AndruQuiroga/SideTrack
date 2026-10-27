"""Similar audio: cosine neighbours within one model, revision and pipeline (ADR 0004)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session

from sidetrack.analysis.models import AudioAsset, AudioEmbedding

from .jobs import is_current
from .registry import PIPELINE, enabled_model


@dataclass(frozen=True)
class Neighbour:
    asset_id: UUID
    sha256: str
    kind: str
    seed_artist: str
    seed_title: str
    track_id: UUID | None
    similarity: float


@dataclass(frozen=True)
class Neighbours:
    asset_id: UUID
    model: str
    embedded: bool
    neighbours: list[Neighbour] = field(default_factory=list)


def resolve_asset(db: Session, key: str) -> AudioAsset | None:
    """An asset by SHA-256 or ID, for the operator's `neighbours` command."""

    try:
        asset_id: UUID | None = UUID(key)
    except ValueError:
        asset_id = None
    return db.scalar(
        select(AudioAsset).where(or_(AudioAsset.sha256 == key.lower(), AudioAsset.id == asset_id))
    )


def similar_assets(db: Session, asset_id: UUID, model: str, k: int = 10) -> Neighbours:
    """Other assets ranked by cosine similarity, highest first, at most ``k``.

    Excludes the query asset's own track, or its seed artist and title when it has no track.
    An asset without a current embedding for ``model`` reports ``embedded=False``.
    """

    spec = enabled_model(model)
    query = db.scalar(
        select(AudioEmbedding).where(
            AudioEmbedding.asset_id == asset_id, AudioEmbedding.model == spec.name
        )
    )
    asset = db.get(AudioAsset, asset_id)
    if asset is None or query is None or not is_current(query, spec):
        return Neighbours(asset_id, spec.name, embedded=False)

    if asset.track_id is not None:
        own = AudioAsset.track_id == asset.track_id
    else:
        own = and_(
            func.lower(AudioAsset.seed_artist) == asset.seed_artist.lower(),
            func.lower(AudioAsset.seed_title) == asset.seed_title.lower(),
        )
    distance = AudioEmbedding.embedding.cosine_distance(query.embedding)
    rows = db.execute(
        select(AudioAsset, (1 - distance).label("similarity"))
        .join(AudioEmbedding, AudioEmbedding.asset_id == AudioAsset.id)
        .where(
            AudioEmbedding.model == spec.name,
            AudioEmbedding.checkpoint_revision == spec.revision,
            AudioEmbedding.pipeline == PIPELINE,
            AudioAsset.id != asset_id,
            or_(not_(own), own.is_(None)),
        )
        .order_by(distance, AudioAsset.id)
        .limit(k)
    ).all()
    return Neighbours(
        asset_id,
        spec.name,
        embedded=True,
        neighbours=[
            Neighbour(
                a.id,
                a.sha256,
                a.kind.value,
                a.seed_artist,
                a.seed_title,
                a.track_id,
                float(similarity),
            )
            for a, similarity in rows
        ],
    )
