"""Club membership, maintained by the bot acting as itself (ADR 0009)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sidetrack.club.membership import mark_left, upsert_member
from sidetrack.db import get_db
from sidetrack.identity import auth, policy
from sidetrack.types import ClubRole

router = APIRouter(
    prefix="/club/members",
    tags=["club-members"],
    dependencies=[Depends(policy(auth.CLUB_MEMBERSHIP))],
)

DiscordId = Annotated[str, Path(pattern=r"^\d{17,20}$")]


class MembershipUpdate(BaseModel):
    role: ClubRole


class MembershipRead(BaseModel):
    user_id: str
    role: ClubRole


def _linked_user(db: Session, discord_id: str):
    user_id = auth.resolve_discord_user(db, discord_id)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discord user not linked")
    return user_id


@router.put("/discord/{discord_id}", response_model=MembershipRead)
def put_member(
    discord_id: DiscordId, payload: MembershipUpdate, db: Session = Depends(get_db)
) -> MembershipRead:
    """Record the Discord user as a current member with ``role``; idempotent."""

    user_id = _linked_user(db, discord_id)
    member = upsert_member(db, user_id, payload.role)
    db.commit()
    return MembershipRead(user_id=str(member.user_id), role=member.role)


@router.delete("/discord/{discord_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(discord_id: DiscordId, db: Session = Depends(get_db)) -> Response:
    """Mark the Discord user as having left; their club history is kept."""

    user_id = _linked_user(db, discord_id)
    mark_left(db, user_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
