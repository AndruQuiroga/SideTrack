"""Read model: which YouTube videos a track was played from."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.listening.models import ListenEvent


def track_video_ids(db: Session, user_id: UUID | None = None) -> list[tuple[UUID, str]]:
    """Distinct ``(track_id, youtube_id)`` pairs from listen metadata.

    Reads ``metadata.listenbrainz.youtube_id``. No listen rows cross the boundary: only the
    pairs, optionally for one user.
    """

    video = ListenEvent.metadata_["listenbrainz"]["youtube_id"].as_string()
    query = (
        select(ListenEvent.track_id, video)
        .where(video.is_not(None), video != "")
        .distinct()
        .order_by(ListenEvent.track_id, video)
    )
    if user_id is not None:
        query = query.where(ListenEvent.user_id == user_id)
    return [(track_id, youtube_id) for track_id, youtube_id in db.execute(query)]
