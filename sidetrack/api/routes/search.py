"""Search endpoint backed by the database with MusicBrainz fallback for albums."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from sidetrack.catalog import Album, Track, upsert_album_from_release_group
from sidetrack.club import ClubMember
from sidetrack.db import get_db
from sidetrack.identity import Principal, User, auth, policy

router = APIRouter(tags=["search"])


@router.get("/search")
async def search(
    q: str = Query("", description="Free text search query"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CATALOG_READ)),
) -> dict[str, list[dict[str, object]]]:
    query = (q or "").strip()
    like = f"%{query}%"

    # Users
    # Only club members find people, and only other current members.
    users_q = (
        select(User)
        .join(ClubMember, ClubMember.user_id == User.id)
        .where(ClubMember.left_at.is_(None))
        .where(or_(User.display_name.ilike(like), User.handle.ilike(like)))
        .limit(10)
    )
    find_users = bool(query) and auth.is_member_actor(db, principal)
    users_rows = db.execute(users_q).scalars().all() if find_users else []
    users = [
        {"id": str(u.id), "display_name": u.display_name, "handle": u.handle} for u in users_rows
    ]

    # Albums
    albums_q = (
        select(Album).where(or_(Album.title.ilike(like), Album.artist_name.ilike(like))).limit(10)
    )
    album_rows = db.execute(albums_q).scalars().all() if query else []
    # If no albums found, attempt MB search and upsert (treat entire query as album title)
    if not album_rows and len(query) >= 3:
        try:
            album = upsert_album_from_release_group(db, artist_name=None, album_title=query)
            if album is not None:
                album_rows = [album]
        except Exception:
            pass

    albums = [
        {
            "id": str(a.id),
            "title": a.title,
            "artist_name": a.artist_name,
            "release_year": a.release_year,
        }
        for a in album_rows
    ]

    # Tracks (include album title via relationship)
    tracks_q = (
        select(Track)
        .options(joinedload(Track.album))
        .where(or_(Track.title.ilike(like), Track.artist_name.ilike(like)))
        .limit(10)
    )
    track_rows = db.execute(tracks_q).scalars().all() if query else []
    tracks = [
        {
            "id": str(t.id),
            "title": t.title,
            "artist_name": t.artist_name,
            "album_title": t.album.title if t.album else None,
        }
        for t in track_rows
    ]

    return {"users": users, "albums": albums, "tracks": tracks}
