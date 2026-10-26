"""Follow / social-graph endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sidetrack.db import get_db
from sidetrack.identity import auth
from sidetrack.identity.auth import Principal, policy
from sidetrack.identity.models import Follow, User
from sidetrack.schemas import UserRead

router = APIRouter(prefix="/users", tags=["social"])


def _require_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.post("/{user_id}/follow/{target_id}", status_code=status.HTTP_201_CREATED)
async def follow_user(
    user_id: UUID,
    target_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.SELF)),
) -> dict[str, str]:
    """Create a follow relationship from the acting user (user_id) → target_id."""

    auth.require_self(principal, user_id)

    if user_id == target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot follow yourself."
        )
    _require_user(db, user_id)
    _require_user(db, target_id)

    follow = Follow(follower_id=user_id, followee_id=target_id)
    db.add(follow)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Already following this user."
        )
    return {"status": "following"}


@router.delete("/{user_id}/follow/{target_id}")
async def unfollow_user(
    user_id: UUID,
    target_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.SELF)),
) -> Response:
    """Remove a follow relationship from the acting user (user_id) → target_id."""

    auth.require_self(principal, user_id)

    follow = db.execute(
        select(Follow).where(
            Follow.follower_id == user_id,
            Follow.followee_id == target_id,
        )
    ).scalar_one_or_none()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Follow relationship not found."
        )

    db.delete(follow)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/followers", response_model=list[UserRead])
async def list_followers(
    user_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CLUB_READ)),
) -> list[UserRead]:
    """Return users who follow user_id. Club members only."""

    principal.require_actor()
    auth.require_member(db, principal)

    _require_user(db, user_id)
    follows = db.scalars(select(Follow).where(Follow.followee_id == user_id)).all()
    follower_ids = [f.follower_id for f in follows]
    if not follower_ids:
        return []
    users = db.scalars(select(User).where(User.id.in_(follower_ids))).all()
    return list(users)


@router.get("/{user_id}/following", response_model=list[UserRead])
async def list_following(
    user_id: UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(policy(auth.CLUB_READ)),
) -> list[UserRead]:
    """Return users that user_id follows. Club members only."""

    principal.require_actor()
    auth.require_member(db, principal)

    _require_user(db, user_id)
    follows = db.scalars(select(Follow).where(Follow.follower_id == user_id)).all()
    followee_ids = [f.followee_id for f in follows]
    if not followee_ids:
        return []
    users = db.scalars(select(User).where(User.id.in_(followee_ids))).all()
    return list(users)
