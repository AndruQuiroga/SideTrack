"""Track similarity endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from sidetrack.common.models import Track

from ..db import get_db

router = APIRouter()


@router.get("/similar/track/{track_id}")
async def get_similar_tracks(
    track_id: int,
    k: int = Query(20, ge=1, le=100),
    diversity_penalty: float = Query(0.3, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Return tracks similar to ``track_id``.

    Results are obtained using pgvector distance and then reranked to reduce
    consecutive results from the same artist or label.
    """

    base = await db.get(Track, track_id)
    if base is None or base.embeddings is None:
        raise HTTPException(status_code=404, detail="track not found")

    # Fetch a larger candidate set ordered by vector distance
    stmt = text(
        "SELECT t.track_id, t.artist_id, r.label, 1 - (t.embeddings <=> :vec) AS score "
        "FROM track t LEFT JOIN release r ON t.release_id = r.release_id "
        "WHERE t.track_id != :tid "
        "ORDER BY t.embeddings <=> :vec "
        "LIMIT :limit"
    )
    rows = (
        await db.execute(
            stmt, {"vec": base.embeddings, "tid": track_id, "limit": k * 4}
        )
    ).all()

    seen_artists: set[int | None] = set()
    seen_labels: set[str | None] = set()
    results: list[dict[str, float | int]] = []

    for tid, artist_id, label, score in rows:
        penalty = 0.0
        if artist_id in seen_artists:
            penalty += diversity_penalty
        if label in seen_labels:
            penalty += diversity_penalty
        seen_artists.add(artist_id)
        seen_labels.add(label)
        results.append({"track_id": int(tid), "score": float(score - penalty)})
        if len(results) >= k:
            break

    return results

