"""Recommendations backed by listens/club data with DB fallback.

Preserves the stubbed response shape used by the web app:
list[ { type: 'album'|'track', id, title, artist_name, [album_title], [reason] } ]
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import Album, ListenEvent, Track, Rating

router = APIRouter(tags=["recommendations"])


@router.get("/recommendations")
async def get_recommendations(
    user_id: str = Query(..., description="User ID for whom to fetch recommendations"),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    # 1) Seed from user's top artists by listen count
    top_artists_stmt = (
        select(Track.artist_name, func.count(ListenEvent.id).label("cnt"))
        .join(Track, ListenEvent.track_id == Track.id)
        .where(ListenEvent.user_id == user_id)
        .group_by(Track.artist_name)
        .order_by(func.count(ListenEvent.id).desc())
        .limit(3)
    )
    top_artists = [row[0] for row in db.execute(top_artists_stmt).all()]

    if top_artists:
        albums_stmt = (
            select(Album)
            .where(Album.artist_name.in_(top_artists))
            .order_by(Album.release_year.desc().nullslast())
            .limit(10)
        )
        for a in db.execute(albums_stmt).scalars().all():
            items.append(
                {
                    "type": "album",
                    "id": str(a.id),
                    "title": a.title,
                    "artist_name": a.artist_name,
                    "reason": "from your top artists",
                }
            )

    # 2) Add a few top tracks by play count as track recs
    top_tracks_stmt = (
        select(Track, func.count(ListenEvent.id).label("cnt"))
        .join(Track, ListenEvent.track_id == Track.id)
        .where(ListenEvent.user_id == user_id)
        .group_by(Track.id)
        .order_by(func.count(ListenEvent.id).desc())
        .limit(3)
    )
    for t, _cnt in db.execute(top_tracks_stmt).all():
        items.append(
            {
                "type": "track",
                "id": str(t.id),
                "title": t.title,
                "artist_name": t.artist_name,
                "album_title": None,
                "reason": "because you listen often",
            }
        )

    # 3) Fallback to club trending albums if user has no listens
    if not items:
        trending_stmt = (
            select(Album, func.avg(Rating.value).label("avg"), func.count(Rating.id).label("cnt"))
            .join(Album, Rating.album_id == Album.id)
            .group_by(Album.id)
            .order_by(func.count(Rating.id).desc(), func.avg(Rating.value).desc())
            .limit(3)
        )
        for a, _avg, _cnt in db.execute(trending_stmt).all():
            items.append(
                {
                    "type": "album",
                    "id": str(a.id),
                    "title": a.title,
                    "artist_name": a.artist_name,
                    "reason": "club trending",
                }
            )

    return items
