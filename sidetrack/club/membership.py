"""Club membership and roles (ADR 0009). Only the bot and the operator change membership."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from sidetrack.club.models import ClubMember
from sidetrack.types import ClubRole


def member_role(db: Session, user_id: UUID) -> ClubRole | None:
    """Return the user's current role, or None when they are not a member."""

    member = db.get(ClubMember, user_id)
    if member is None or member.left_at is not None:
        return None
    return member.role


def is_member(db: Session, user_id: UUID) -> bool:
    return member_role(db, user_id) is not None


def upsert_member(db: Session, user_id: UUID, role: ClubRole) -> ClubMember:
    """Make the user a current member with ``role``; rejoining clears ``left_at``.

    The caller commits.
    """

    member = db.get(ClubMember, user_id, with_for_update=True)
    if member is None:
        member = ClubMember(user_id=user_id, role=role, joined_at=datetime.now(UTC))
        db.add(member)
    else:
        if member.left_at is not None:
            member.joined_at = datetime.now(UTC)
            member.left_at = None
        member.role = role
    db.flush()
    return member


def mark_left(db: Session, user_id: UUID) -> bool:
    """End the user's membership, keeping their club history. False if not a member."""

    member = db.get(ClubMember, user_id, with_for_update=True)
    if member is None or member.left_at is not None:
        return False
    member.left_at = datetime.now(UTC)
    db.flush()
    return True
