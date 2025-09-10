"""Endpoints for computing listening transitions."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Listen, Track, Artist, LastfmTags

from ..db import get_db
from ..security import get_current_user

router = APIRouter()


def _top_genre(tags: dict | None) -> str | None:
    if not tags:
        return None
    try:
        return max(tags.items(), key=lambda x: x[1])[0]
    except ValueError:  # pragma: no cover - empty dict
        return None


@router.get("/flows")
async def list_flows(
    level: str = Query("artist", pattern="^(artist|genre)$"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return transition probabilities between artists or genres for the current user.

    The result is a list of directed edges with conditional probabilities
    :math:`p(\text{next}|\text{current})` and a baseline probability computed
    across all users. The ``lift`` field highlights unusually strong edges.
    """

    stmt = (
        select(Listen.user_id, Listen.played_at, Artist.name, LastfmTags.tags)
        .join(Track, Track.track_id == Listen.track_id)
        .join(Artist, Artist.artist_id == Track.artist_id, isouter=True)
        .join(LastfmTags, LastfmTags.track_id == Track.track_id, isouter=True)
        .order_by(Listen.user_id, Listen.played_at)
    )
    rows = (await db.execute(stmt)).all()

    user_edges: defaultdict[tuple[str, str], int] = defaultdict(int)
    user_counts: defaultdict[str, int] = defaultdict(int)
    global_edges: defaultdict[tuple[str, str], int] = defaultdict(int)
    global_counts: defaultdict[str, int] = defaultdict(int)
    last_by_user: dict[str, str] = {}

    for uid, _ts, artist, tags in rows:
        label = artist if level == "artist" else _top_genre(tags)
        if not label:
            continue
        prev = last_by_user.get(uid)
        if prev:
            global_edges[(prev, label)] += 1
            global_counts[prev] += 1
            if uid == user_id:
                user_edges[(prev, label)] += 1
                user_counts[prev] += 1
        last_by_user[uid] = label

    edges = []
    for (src, dst), cnt in user_edges.items():
        prob = cnt / user_counts[src] if user_counts[src] else 0.0
        baseline = (
            global_edges[(src, dst)] / global_counts[src]
            if global_counts[src]
            else 0.0
        )
        lift = prob / baseline if baseline > 0 else None
        edges.append(
            {
                "source": src,
                "target": dst,
                "prob": prob,
                "baseline": baseline,
                "lift": lift,
            }
        )
    return {"edges": edges}
