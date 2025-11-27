from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models.club import Nomination, Rating, Week
from apps.api.models.music import Album
from apps.api.models.user import User
from apps.api.schemas import (
    RatingCreate,
    RatingHistogramBin,
    RatingRead,
    RatingSummary,
)

router = APIRouter(tags=["ratings"])


def _require_week(db: Session, week_id: UUID) -> Week:
    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Week not found.",
        )
    if not week.winner_album_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Week does not yet have a winner album to rate.",
        )
    return week


def _require_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def _require_album(db: Session, album_id: UUID) -> Album:
    album = db.get(Album, album_id)
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found.",
        )
    return album


def _validate_nomination(
    db: Session, nomination_id: UUID | None, week_id: UUID, album_id: UUID
) -> Nomination | None:
    if nomination_id is None:
        return None

    nomination = db.get(Nomination, nomination_id)
    if not nomination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nomination not found.",
        )
    if nomination.week_id != week_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nomination does not belong to the requested week.",
        )
    if nomination.album_id != album_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nomination album must match the rated album.",
        )

    return nomination


def _bucket_value(value: float, bin_size: float) -> float:
    quantizer = Decimal(str(bin_size))
    decimal_value = Decimal(str(value))
    steps = (decimal_value / quantizer).to_integral_value(rounding=ROUND_FLOOR)
    return float(steps * quantizer)


@router.get("/ratings", response_model=list[RatingRead])
async def list_ratings(db: Session = Depends(get_db)) -> list[RatingRead]:
    ratings = db.execute(select(Rating)).scalars().all()
    return [RatingRead.model_validate(rating) for rating in ratings]


@router.get("/ratings/{rating_id}", response_model=RatingRead)
async def get_rating(rating_id: UUID, db: Session = Depends(get_db)) -> RatingRead:
    rating = db.get(Rating, rating_id)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found.",
        )
    return RatingRead.model_validate(rating)


@router.post(
    "/weeks/{week_id}/ratings",
    response_model=RatingRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_week_rating(
    week_id: UUID,
    payload: RatingCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> RatingRead:
    week = _require_week(db, week_id)
    _require_user(db, payload.user_id)
    _require_album(db, payload.album_id)
    _validate_nomination(db, payload.nomination_id, week_id, payload.album_id)

    if payload.album_id != week.winner_album_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ratings must target the week's winning album.",
        )

    if not 1.0 <= payload.value <= 5.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ratings must fall between 1.0 and 5.0.",
        )

    existing_rating = db.execute(
        select(Rating).where(
            Rating.week_id == week_id,
            Rating.user_id == payload.user_id,
        )
    ).scalar_one_or_none()
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has already submitted a rating for this week.",
        )

    rating = Rating(
        week_id=week_id,
        user_id=payload.user_id,
        album_id=payload.album_id,
        nomination_id=payload.nomination_id,
        value=payload.value,
        favorite_track=payload.favorite_track,
        review=payload.review,
        created_at=payload.created_at or datetime.now(timezone.utc),
        metadata=payload.metadata,
    )

    db.add(rating)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has already submitted a rating for this week.",
        )

    db.refresh(rating)
    return RatingRead.model_validate(rating)


@router.get(
    "/weeks/{week_id}/ratings/summary",
    response_model=RatingSummary,
)
async def get_week_rating_summary(
    week_id: UUID,
    db: Session = Depends(get_db),
    include_histogram: bool = Query(False, description="Return histogram bins."),
    bin_size: float = Query(0.5, gt=0, description="Histogram bin size."),
) -> RatingSummary:
    _require_week(db, week_id)

    stats = db.execute(
        select(func.avg(Rating.value), func.count(Rating.id)).where(
            Rating.week_id == week_id
        )
    ).one()
    average = float(stats[0]) if stats[0] is not None else None
    count = int(stats[1] or 0)

    histogram: list[RatingHistogramBin] | None = None
    if include_histogram and count:
        values = db.execute(
            select(Rating.value).where(Rating.week_id == week_id)
        ).scalars().all()
        counter: Counter[float] = Counter()
        for value in values:
            counter[_bucket_value(value, bin_size)] += 1

        histogram = [
            RatingHistogramBin(value=bucket, count=bucket_count)
            for bucket, bucket_count in sorted(counter.items())
        ]

    return RatingSummary(average=average, count=count, histogram=histogram)
