"""Cohort-related API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..security import get_current_user

router = APIRouter(prefix="/cohorts")


@router.get("/influence")
async def list_influence(
    metric: str = Query("energy"),
    window: str = Query("12w"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Return top artist/label contributions for the given metric."""

    # In lieu of a real implementation, return placeholder data. A future
    # version will compute these scores from listening history.
    return [
        {
            "name": "Artist A",
            "type": "artist",
            "score": 0.8,
            "confidence": 0.9,
            "trend": [0.3, 0.5, 0.7, 0.8],
        },
        {
            "name": "Label X",
            "type": "label",
            "score": 0.6,
            "confidence": 0.85,
            "trend": [0.2, 0.4, 0.5, 0.6],
        },
    ]
