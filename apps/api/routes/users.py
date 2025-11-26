"""User-facing API stubs."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    """Return a static list of users until persistence is wired up."""

    _ = db  # placeholder to show dependency wiring
    return [
        UserRead(
            id=uuid4(),
            display_name="Demo User",
            handle="demo",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
    ]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserRead:
    """Return a representative user payload."""

    _ = db
    return UserRead(
        id=user_id,
        display_name="Sample Member",
        handle="sample_member",
        created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 2, 1, 12, 0, tzinfo=timezone.utc),
    )
