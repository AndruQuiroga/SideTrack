"""User-facing API stubs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[User])
async def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Return a static list of users until persistence is wired up."""

    _ = db  # placeholder to show dependency wiring
    return [
        User(
            id="user-001",
            email="demo@samples.dev",
            display_name="Demo User",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
    ]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, db: Session = Depends(get_db)) -> User:
    """Return a representative user payload."""

    _ = db
    return User(
        id=user_id,
        email="member@samples.dev",
        display_name="Sample Member",
        created_at=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
