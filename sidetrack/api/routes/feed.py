"""Activity feed endpoints for club and social activity."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from sidetrack.catalog import Album
from sidetrack.club import Rating, Week
from sidetrack.db import get_db
from sidetrack.identity import Principal, User, auth, policy


class FeedEventType(str, Enum):
    RATING = "rating"
    LISTEN = "listen"
    CLUB = "club"
    FOLLOW = "follow"


class FeedItem(BaseModel):
    """An activity item shown in the feed."""

    id: str
    type: FeedEventType
    actor: str
    actor_id: str | None = None
    action: str
    target: str | None = None
    target_link: str | None = None
    rating: float | None = None
    timestamp: datetime
    metadata: dict | None = None


router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=list[FeedItem])
async def get_feed(
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CLUB_READ)),
    user_id: str | None = Query(None, description="Must be the acting user when given."),
    limit: int = Query(20, ge=1, le=100, description="Number of feed items to return"),
) -> list[FeedItem]:
    """Return recent club activity (ratings and winners) for an acting club member."""

    actor = principal.require_actor()
    if user_id is not None and user_id != str(actor):
        raise auth.forbidden("user_id does not match the acting user.")
    auth.require_member(db, principal)
    feed_items: list[FeedItem] = []

    # Fetch recent ratings with user and album data
    rating_stmt = (
        select(Rating, User, Album, Week)
        .join(User, Rating.user_id == User.id)
        .join(Album, Rating.album_id == Album.id)
        .join(Week, Rating.week_id == Week.id)
        .order_by(Rating.created_at.desc())
        .limit(limit)
    )
    for rating, user, album, week in db.execute(rating_stmt).all():
        feed_items.append(
            FeedItem(
                id=f"rating-{rating.id}",
                type=FeedEventType.RATING,
                actor=user.display_name or user.handle or "Anonymous",
                actor_id=str(user.id),
                action="rated",
                target=f"{album.title} — {album.artist_name}",
                target_link=f"/club/weeks/{week.id}",
                rating=rating.value,
                timestamp=rating.created_at,
                metadata={
                    "album_id": str(album.id),
                    "week_id": str(week.id),
                    "week_label": week.label,
                    "review": rating.review[:100] if rating.review else None,
                    "favorite_track": rating.favorite_track,
                },
            )
        )

    # Fetch recent weeks with winners (club announcements)
    week_stmt = (
        select(Week, Album)
        .outerjoin(Album, Week.winner_album_id == Album.id)
        .where(Week.winner_album_id.is_not(None))
        .order_by(Week.created_at.desc())
        .limit(5)
    )
    for week, album in db.execute(week_stmt).all():
        if album:
            feed_items.append(
                FeedItem(
                    id=f"club-{week.id}",
                    type=FeedEventType.CLUB,
                    actor="bot",
                    action=f"announced winner for {week.label}",
                    target=f"{album.title} — {album.artist_name}",
                    target_link=f"/club/weeks/{week.id}",
                    timestamp=week.created_at,
                    metadata={
                        "week_number": week.week_number,
                        "album_id": str(album.id),
                    },
                )
            )

    # Sort all items by timestamp descending and limit
    feed_items.sort(key=lambda x: x.timestamp, reverse=True)
    return feed_items[:limit]
