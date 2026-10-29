"""Member/bot reads of independently numbered historical Singles Night sessions."""

from math import fsum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import Principal, User, auth, policy
from sidetrack.schemas.singles import SinglesSessionDetail, SinglesSessionRead

from ..artwork import SinglesSongArtwork
from ..history.sources import safe_url, snowflake
from ..history_models import (
    HistorySource,
    SinglesRating,
    SinglesSession,
    SinglesSong,
    SinglesSubmission,
)

router = APIRouter(prefix="/club/singles-nights", tags=["singles-nights"])


def _source(session, message=None):
    base = f"https://discord.com/channels/{snowflake(session.guild_id)}/{snowflake(session.source_thread_id)}"
    return f"{base}/{snowflake(message)}" if message else base


def _sessions():
    return (
        select(
            SinglesSession,
            func.count(distinct(SinglesSong.id)),
            func.count(distinct(SinglesRating.id)),
        )
        .outerjoin(SinglesSong, SinglesSong.session_id == SinglesSession.id)
        .outerjoin(
            SinglesRating,
            SinglesRating.session_id == SinglesSession.id,
        )
        .group_by(SinglesSession.id)
    )


def _summary(session, songs, ratings):
    return {
        "id": session.id,
        "week_number": session.week_number,
        "event_date": session.event_date,
        "event_at": session.event_at,
        "original_label": session.original_label,
        "source_url": _source(session),
        "song_count": songs,
        "rating_count": ratings,
    }


@router.get("", response_model=list[SinglesSessionRead])
def list_singles_nights(
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CLUB_READ)),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    auth.require_member(db, principal)
    query = (
        _sessions()
        .order_by(
            SinglesSession.event_date.desc().nulls_last(),
            SinglesSession.week_number.desc().nulls_last(),
            SinglesSession.id,
        )
        .offset(offset)
        .limit(limit)
    )
    return [_summary(*row) for row in db.execute(query)]


@router.get("/{session_id}", response_model=SinglesSessionDetail)
def get_singles_night(
    session_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CLUB_READ)),
):
    auth.require_member(db, principal)
    row = db.execute(_sessions().where(SinglesSession.id == session_id)).first()
    if row is None:
        raise HTTPException(404, "Singles Night session not found.")
    session = row[0]
    songs = db.scalars(
        select(SinglesSong)
        .where(SinglesSong.session_id == session_id)
        .order_by(
            SinglesSong.position,
            SinglesSong.id,
        )
    ).all()
    submissions = db.execute(
        select(SinglesSubmission, User.display_name)
        .join(
            User,
            User.id == SinglesSubmission.user_id,
        )
        .where(SinglesSubmission.session_id == session_id)
        .order_by(
            SinglesSubmission.submitted_at,
            SinglesSubmission.id,
        )
    ).all()
    ratings = db.execute(
        select(SinglesRating, User.display_name)
        .join(
            User,
            User.id == SinglesRating.user_id,
        )
        .where(SinglesRating.session_id == session_id)
        .order_by(
            SinglesRating.created_at,
            SinglesRating.id,
        )
    ).all()
    target_ids = [song.id for song in songs] + [rating.id for rating, _ in ratings]
    markers = db.scalars(
        select(HistorySource)
        .where(
            HistorySource.target_id.in_(target_ids),
            HistorySource.target_kind.in_(["singles_song", "singles_rating"]),
        )
        .order_by(HistorySource.source_key)
    ).all()
    links: dict[UUID, str] = {}
    for marker in markers:
        links.setdefault(marker.target_id, _source(session, marker.message_id))
    result = _summary(*row)
    artwork = {
        art.song_id: art
        for art in db.scalars(
            select(SinglesSongArtwork).where(SinglesSongArtwork.song_id.in_([s.id for s in songs]))
        )
    }
    result["songs"] = [
        {
            "id": song.id,
            "title": song.title,
            "artist_name": song.artist_name,
            "url": safe_url(song.url),
            "cover_url": safe_url(artwork[song.id].cover_url) if song.id in artwork else None,
            "artwork_source_url": safe_url(artwork[song.id].provider_url)
            if song.id in artwork
            else None,
            "source_url": links.get(song.id),
            "rating_summary": {
                phase: {
                    "count": len(values),
                    "average": fsum(values) / len(values) if values else None,
                }
                for phase in ("first", "final")
                for values in [
                    [
                        rating.value
                        for rating, _ in ratings
                        if rating.song_id == song.id and rating.phase == phase
                    ]
                ]
            },
            "submissions": [
                {
                    "user_id": contribution.user_id,
                    "display_name": name,
                    "submitted_at": contribution.submitted_at,
                }
                for contribution, name in submissions
                if contribution.song_id == song.id
            ],
            "ratings": [
                {
                    "id": rating.id,
                    "user_id": rating.user_id,
                    "display_name": name,
                    "phase": rating.phase,
                    "value": rating.value,
                    "review": rating.review,
                    "created_at": rating.created_at,
                    "source_url": links.get(rating.id),
                }
                for rating, name in ratings
                if rating.song_id == song.id
            ],
        }
        for song in songs
    ]
    return result
