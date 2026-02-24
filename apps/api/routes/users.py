"""User and linked account endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import LinkedAccount, ProviderType, User
from apps.api.models.listening import ListenEvent
from apps.api.models.music import Track
from apps.api.schemas import (
    LinkedAccountCreate,
    LinkedAccountRead,
    UserCreate,
    UserRead,
    UserUpdate,
)


class RecentListenRead(BaseModel):
    track_name: str
    artist_name: str
    album_name: str | None = None
    listened_at: datetime
    source: str | None = None


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of users to return."),
    offset: int = Query(0, ge=0, description="Number of users to skip."),
) -> list[UserRead]:
    """Return users in the system."""

    users = db.scalars(select(User).offset(offset).limit(limit)).all()
    return users


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Create a user record (api/schema-core)."""

    user = User(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # unique handle collision
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this handle already exists",
        ) from exc

    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserRead:
    """Return a user by ID, or raise 404 if missing."""

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db)
) -> UserRead:
    """Update mutable user fields (display_name, handle)."""

    user = _ensure_user_exists(db, user_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Handle already taken",
        ) from exc
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> None:
    """Delete a user and cascade-remove all owned records."""

    user = _ensure_user_exists(db, user_id)
    db.delete(user)
    db.commit()


@router.get("/{user_id}/linked-accounts", response_model=list[LinkedAccountRead])
async def list_linked_accounts(
    user_id: UUID, db: Session = Depends(get_db)
) -> list[LinkedAccountRead]:
    """List linked accounts for a specific user."""

    _ensure_user_exists(db, user_id)
    stmt = select(LinkedAccount).where(LinkedAccount.user_id == user_id)
    return db.scalars(stmt).all()


@router.post(
    "/{user_id}/linked-accounts",
    response_model=LinkedAccountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_linked_account(
    user_id: UUID, payload: LinkedAccountCreate, db: Session = Depends(get_db)
) -> LinkedAccountRead:
    """Create a linked account for a user with provider-specific validation."""

    _ensure_user_exists(db, user_id)

    account_data = payload.model_copy(update={"user_id": user_id}).model_dump()
    account = LinkedAccount(**account_data)
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:  # Unique constraint violation
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Linked account already exists for this provider_user_id",
        ) from exc

    db.refresh(account)
    return account


@router.delete(
    "/{user_id}/linked-accounts/{provider}/{provider_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_linked_account(
    user_id: UUID,
    provider: ProviderType,
    provider_user_id: str,
    db: Session = Depends(get_db),
) -> None:
    """Delete a linked account identified by provider and external ID."""

    _ensure_user_exists(db, user_id)
    stmt = select(LinkedAccount).where(
        LinkedAccount.user_id == user_id,
        LinkedAccount.provider == provider,
        LinkedAccount.provider_user_id == provider_user_id,
    )
    account = db.scalars(stmt).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Linked account not found"
        )

    db.delete(account)
    db.commit()


@router.get("/lookup/by-provider/{provider}/{provider_user_id}", response_model=UserRead)
async def lookup_user_by_provider(
    provider: ProviderType, provider_user_id: str, db: Session = Depends(get_db)
) -> UserRead:
    """Resolve a user via a provider-specific identifier."""

    stmt = select(LinkedAccount).where(
        LinkedAccount.provider == provider,
        LinkedAccount.provider_user_id == provider_user_id,
    )
    account = db.scalars(stmt).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Linked account not found"
        )

    return account.user


@router.get("/{user_id}/listening/recent", response_model=list[RecentListenRead])
async def list_user_recent_listens(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Number of records to skip."),
    db: Session = Depends(get_db),
) -> list[RecentListenRead]:
    """Return recent listen events for a user, joined with track metadata."""

    _ensure_user_exists(db, user_id)
    stmt = (
        select(ListenEvent, Track)
        .join(Track, ListenEvent.track_id == Track.id)
        .where(ListenEvent.user_id == user_id)
        .order_by(ListenEvent.played_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    return [
        RecentListenRead(
            track_name=track.title,
            artist_name=track.artist_name,
            listened_at=listen.played_at,
            source=listen.source.value if listen.source else None,
        )
        for listen, track in rows
    ]


def _ensure_user_exists(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
