"""Vote endpoints backed by the SQLAlchemy models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models.club import Nomination, Vote, Week
from services.api.models.user import User
from services.api.schemas import VoteCreate, VoteRead

router = APIRouter(tags=["votes"])


@router.get("/votes", response_model=list[VoteRead])
async def list_votes(
    db: Session = Depends(get_db),
    week_id: UUID | None = Query(None),
    user_id: UUID | None = Query(None),
    rank: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of votes to return."),
    offset: int = Query(0, ge=0, description="Number of votes to skip."),
) -> list[VoteRead]:
    """Return votes, optionally filtered by week, user, or rank."""

    query = select(Vote)
    if week_id is not None:
        query = query.where(Vote.week_id == week_id)
    if user_id is not None:
        query = query.where(Vote.user_id == user_id)
    if rank is not None:
        query = query.where(Vote.rank == rank)

    votes = db.execute(query.offset(offset).limit(limit)).scalars().all()
    return [VoteRead.model_validate(vote) for vote in votes]


@router.get("/votes/{vote_id}", response_model=VoteRead)
async def get_vote(vote_id: UUID, db: Session = Depends(get_db)) -> VoteRead:
    """Return a single vote by ID."""

    vote = db.get(Vote, vote_id)
    if not vote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vote not found.")
    return VoteRead.model_validate(vote)


@router.post(
    "/weeks/{week_id}/votes",
    response_model=VoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_week_vote(
    week_id: UUID,
    payload: VoteCreate,
    db: Session = Depends(get_db),
) -> VoteRead:
    """Submit a vote for a nomination in a week. Returns 409 if the user has already
    voted with the same rank for this week."""

    week = db.get(Week, week_id)
    if not week:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Week not found.")

    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    nomination = db.get(Nomination, payload.nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found.")
    if nomination.week_id != week_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nomination does not belong to this week.",
        )

    if payload.rank not in (1, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rank must be 1 (first choice) or 2 (second choice).",
        )

    existing = db.execute(
        select(Vote).where(
            Vote.week_id == week_id,
            Vote.user_id == payload.user_id,
            Vote.rank == payload.rank,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has already submitted a vote with this rank for this week.",
        )

    vote = Vote(
        week_id=week_id,
        nomination_id=payload.nomination_id,
        user_id=payload.user_id,
        rank=payload.rank,
        submitted_at=payload.submitted_at or datetime.now(UTC),
    )
    db.add(vote)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has already submitted a vote with this rank for this week.",
        )

    db.refresh(vote)
    return VoteRead.model_validate(vote)
