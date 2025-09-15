"""Utilities for merging tag data from multiple sources.

This module provides helpers for combining Last.fm and MusicBrainz tag data
into a canonical tag space and for deriving aggregate information such as
TF–IDF scores or label rollups. The functions are intentionally lightweight so
that they can be reused in both batch jobs and API handlers.
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.analytics.tags import canonicalize_tag, compute_user_tfidf, label_rollups, merge_tags
from sidetrack.common.models import MBLabel, MBTag

# Re-export helpers from ``sidetrack.analytics.tags`` for backward compatibility
__all__ = [
    "canonicalize_tag",
    "merge_tags",
    "compute_user_tfidf",
    "label_rollups",
    "persist_mb_tags",
    "persist_mb_label",
]


async def persist_mb_tags(db: AsyncSession, track_id: int, tags: Mapping[str, float]) -> None:
    """Persist tag scores for a track to the ``mb_tag`` table."""

    await db.execute(delete(MBTag).where(MBTag.track_id == track_id))
    for tag, score in tags.items():
        db.add(MBTag(track_id=track_id, tag=tag, score=float(score)))
    await db.commit()


async def persist_mb_label(
    db: AsyncSession, track_id: int, rollup: Mapping[str, str | None]
) -> None:
    """Persist label rollup information to the ``mb_label`` table."""

    await db.execute(delete(MBLabel).where(MBLabel.track_id == track_id))
    db.add(
        MBLabel(
            track_id=track_id,
            primary_label=rollup.get("primary_label"),
            label_country=rollup.get("label_country"),
            era=rollup.get("era"),
        )
    )
    await db.commit()
