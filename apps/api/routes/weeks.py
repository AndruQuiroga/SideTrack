"""Week endpoints with placeholder payloads."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.schemas.core import Week

router = APIRouter(prefix="/weeks", tags=["weeks"])


@router.get("/", response_model=list[Week])
async def list_weeks(db: Session = Depends(get_db)) -> list[Week]:
    """Return a static set of club weeks."""

    _ = db
    return [
        Week(
            id=1,
            slug="week-001",
            title="Week One",
            starts_at=date(2024, 7, 1),
            ends_at=date(2024, 7, 7),
            status="archived",
        )
    ]


@router.get("/{week_id}", response_model=Week)
async def get_week(week_id: int, db: Session = Depends(get_db)) -> Week:
    """Return a single representative week."""

    _ = db
    return Week(
        id=week_id,
        slug=f"week-{week_id:03d}",
        title="Placeholder Week",
        starts_at=date(2024, 7, 8),
        ends_at=date(2024, 7, 14),
        status="planning",
    )
