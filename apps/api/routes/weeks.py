"""Week endpoints backed by the SQLAlchemy models."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models.club import Nomination, Rating, Vote, Week
from apps.api.schemas import (
    NominationRead,
    NominationWithStats,
    RatingAggregate,
    VoteAggregate,
    WeekAggregates,
    WeekCreate,
    WeekDetail,
    WeekRead,
    WeekUpdate,
)

router = APIRouter(prefix="/weeks", tags=["weeks"])


def _validate_timeline(
    discussion_at: datetime | None,
    nominations_close_at: datetime | None,
    poll_close_at: datetime | None,
) -> None:
    """Ensure club milestones occur in chronological order."""

    if nominations_close_at and poll_close_at and nominations_close_at > poll_close_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nominations must close on or before the poll close time.",
        )
    if poll_close_at and discussion_at and poll_close_at > discussion_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Polls must close before the discussion time.",
        )
    if nominations_close_at and discussion_at and nominations_close_at > discussion_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nominations must close before the discussion time.",
        )


def _find_existing_week(db: Session, payload: WeekCreate) -> Week | None:
    """Return an existing week for idempotent bot replays."""

    filters = []
    if payload.week_number is not None:
        filters.append(Week.week_number == payload.week_number)
    if payload.label:
        filters.append(func.lower(Week.label) == payload.label.lower())
    if payload.legacy_week_id:
        filters.append(Week.legacy_week_id == payload.legacy_week_id)

    if not filters:
        return None

    return db.execute(select(Week).where(or_(*filters))).scalar_one_or_none()


def _fetch_vote_stats(db: Session, week_ids: list[UUID]) -> dict[tuple[UUID, UUID], VoteAggregate]:
    vote_rows = db.execute(
        select(
            Vote.week_id,
            Vote.nomination_id,
            func.sum(
                case((Vote.rank == 1, 2), (Vote.rank == 2, 1), else_=0)
            ).label("points"),
            func.sum(case((Vote.rank == 1, 1), else_=0)).label("first_place"),
            func.sum(case((Vote.rank == 2, 1), else_=0)).label("second_place"),
            func.count(Vote.id).label("total_votes"),
        )
        .where(Vote.week_id.in_(week_ids))
        .group_by(Vote.week_id, Vote.nomination_id)
    ).all()

    stats: dict[tuple[UUID, UUID], VoteAggregate] = {}
    for row in vote_rows:
        stats[(row.week_id, row.nomination_id)] = VoteAggregate(
            points=int(row.points or 0),
            first_place=int(row.first_place or 0),
            second_place=int(row.second_place or 0),
            total_votes=int(row.total_votes or 0),
        )
    return stats


def _fetch_rating_stats(
    db: Session, week_ids: list[UUID]
) -> tuple[dict[tuple[UUID, UUID | None], RatingAggregate], dict[UUID, RatingAggregate]]:
    rating_rows = db.execute(
        select(
            Rating.week_id,
            Rating.nomination_id,
            func.avg(Rating.value).label("average"),
            func.count(Rating.id).label("count"),
        )
        .where(Rating.week_id.in_(week_ids))
        .group_by(Rating.week_id, Rating.nomination_id)
    ).all()

    per_nomination: dict[tuple[UUID, UUID | None], RatingAggregate] = {}
    for row in rating_rows:
        per_nomination[(row.week_id, row.nomination_id)] = RatingAggregate(
            average=float(row.average) if row.average is not None else None,
            count=int(row.count or 0),
        )

    week_rows = db.execute(
        select(
            Rating.week_id,
            func.avg(Rating.value).label("average"),
            func.count(Rating.id).label("count"),
        )
        .where(Rating.week_id.in_(week_ids))
        .group_by(Rating.week_id)
    ).all()

    per_week: dict[UUID, RatingAggregate] = {}
    for row in week_rows:
        per_week[row.week_id] = RatingAggregate(
            average=float(row.average) if row.average is not None else None,
            count=int(row.count or 0),
        )

    return per_nomination, per_week


def _build_week_details(db: Session, weeks: list[Week]) -> list[WeekDetail]:
    if not weeks:
        return []

    week_ids = [week.id for week in weeks]
    nominations = db.execute(
        select(Nomination).where(Nomination.week_id.in_(week_ids))
    ).scalars().all()
    nominations_by_week: dict[UUID, list[Nomination]] = defaultdict(list)
    for nomination in nominations:
        nominations_by_week[nomination.week_id].append(nomination)

    vote_stats = _fetch_vote_stats(db, week_ids)
    rating_stats, week_rating_stats = _fetch_rating_stats(db, week_ids)

    response: list[WeekDetail] = []
    for week in weeks:
        week_nomination_entities = nominations_by_week.get(week.id, [])
        nomination_payloads: list[NominationWithStats] = []
        for nomination in week_nomination_entities:
            vote_summary = vote_stats.get(
                (week.id, nomination.id),
                VoteAggregate(points=0, first_place=0, second_place=0, total_votes=0),
            )
            rating_summary = rating_stats.get(
                (week.id, nomination.id),
                RatingAggregate(average=None, count=0),
            )

            nomination_payloads.append(
                NominationWithStats(
                    **NominationRead.model_validate(nomination).model_dump(),
                    vote_summary=vote_summary,
                    rating_summary=rating_summary,
                )
            )

        week_rating = week_rating_stats.get(
            week.id, RatingAggregate(average=None, count=0)
        )
        aggregates = WeekAggregates(
            nomination_count=len(nomination_payloads),
            vote_count=sum(n.vote_summary.total_votes for n in nomination_payloads),
            rating_count=week_rating.count,
            rating_average=week_rating.average,
        )

        response.append(
            WeekDetail(
                **WeekRead.model_validate(week).model_dump(),
                nominations=nomination_payloads,
                aggregates=aggregates,
            )
        )

    return response


@router.get("/", response_model=list[WeekDetail])
async def list_weeks(
    db: Session = Depends(get_db),
    discussion_start: datetime | None = Query(
        None, description="Filter weeks with discussion on/after this timestamp."
    ),
    discussion_end: datetime | None = Query(
        None, description="Filter weeks with discussion on/before this timestamp."
    ),
    has_winner: bool | None = Query(
        None, description="Filter by whether a week has a winner album set."
    ),
) -> list[WeekDetail]:
    """Return club weeks with nomination, vote, and rating aggregates."""

    query = select(Week)
    if discussion_start:
        query = query.where(Week.discussion_at >= discussion_start)
    if discussion_end:
        query = query.where(Week.discussion_at <= discussion_end)
    if has_winner is not None:
        if has_winner:
            query = query.where(Week.winner_album_id.is_not(None))
        else:
            query = query.where(Week.winner_album_id.is_(None))

    weeks = (
        db.execute(
            query.order_by(Week.week_number.desc().nulls_last(), Week.created_at.desc())
        )
        .scalars()
        .all()
    )
    return _build_week_details(db, weeks)


@router.get("/{week_id}", response_model=WeekDetail)
async def get_week(week_id: UUID, db: Session = Depends(get_db)) -> WeekDetail:
    """Return a single week with nested aggregates."""

    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Week not found")

    return _build_week_details(db, [week])[0]


@router.post("/", response_model=WeekDetail, status_code=status.HTTP_201_CREATED)
async def create_week(payload: WeekCreate, db: Session = Depends(get_db)) -> WeekDetail:
    """Create or update a week using idempotent matching fields."""

    _validate_timeline(
        payload.discussion_at, payload.nominations_close_at, payload.poll_close_at
    )

    existing = _find_existing_week(db, payload)
    if existing:
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        target = Week(**payload.model_dump())
        db.add(target)
        db.commit()
        db.refresh(target)

    return _build_week_details(db, [target])[0]


@router.patch("/{week_id}", response_model=WeekDetail)
async def update_week(
    week_id: UUID, payload: WeekUpdate, db: Session = Depends(get_db)
) -> WeekDetail:
    """Apply partial updates to a week while validating the timeline."""

    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Week not found")

    updates = payload.model_dump(exclude_unset=True)
    updated_discussion = updates.get("discussion_at", week.discussion_at)
    updated_nom_close = updates.get("nominations_close_at", week.nominations_close_at)
    updated_poll_close = updates.get("poll_close_at", week.poll_close_at)
    _validate_timeline(updated_discussion, updated_nom_close, updated_poll_close)

    for field, value in updates.items():
        setattr(week, field, value)

    db.commit()
    db.refresh(week)
    return _build_week_details(db, [week])[0]
