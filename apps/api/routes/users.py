"""User and linked account endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import LinkedAccount, ProviderType, User
from apps.api.schemas import LinkedAccountCreate, LinkedAccountRead, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    """Return all users in the system."""

    users = db.scalars(select(User)).all()
    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserRead:
    """Return a user by ID, or raise 404 if missing."""

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked account not found")

    db.delete(account)
    db.commit()


@router.get(
    "/lookup/by-provider/{provider}/{provider_user_id}", response_model=UserRead
)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked account not found")

    return account.user


def _ensure_user_exists(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
