"""Trending endpoints backed by DB aggregates (ratings/listens)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import Album, Rating

router = APIRouter(tags=["trending"])


@router.get("/trending")
async def get_trending(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    # Aggregate ratings by album
    stmt = (
        select(
            Album.id,
            Album.title,
            Album.artist_name,
            func.avg(Rating.value).label("avg"),
            func.count(Rating.id).label("cnt"),
        )
        .join(Album, Rating.album_id == Album.id)
        .group_by(Album.id, Album.title, Album.artist_name)
        .order_by(func.count(Rating.id).desc(), func.avg(Rating.value).desc())
        .limit(10)
    )
    rows = db.execute(stmt).all()
    out: list[dict[str, object]] = []
    for r in rows[:3]:
        out.append(
            {
                "type": "album",
                "id": str(r[0]),
                "title": r[1],
                "artist_name": r[2],
                "average": float(r[3]) if r[3] is not None else None,
                "count": int(r[4]),
            }
        )
    return out
