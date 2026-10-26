"""Compatibility endpoint — real score based on taste profile similarity."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sidetrack.analysis.compatibility import compute_compatibility_score
from sidetrack.db import get_db
from sidetrack.identity import User

router = APIRouter(prefix="/users", tags=["compatibility"])


@router.get("/{user_a}/compatibility/{user_b}")
async def get_compatibility(
    user_a: UUID,
    user_b: UUID,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return a compatibility score (0-100) between two users.

    Uses cosine similarity of audio-feature taste profiles when available,
    falls back to genre histogram overlap.
    """

    if not db.get(User, user_a):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User A not found.")
    if not db.get(User, user_b):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User B not found.")

    score, details = compute_compatibility_score(db, user_a, user_b)
    return {"score": score, "overlap": details, "explanation": _explain(details)}


def _explain(details: dict) -> str:
    method = details.get("method", "unknown")
    if method == "cosine_similarity":
        return (
            "Similarity based on audio-feature taste profiles"
            " (energy, valence, danceability, etc.)."
        )
    if method == "genre_overlap":
        return "Similarity based on shared genre listening history."
    return "Not enough listening data to compute a meaningful score yet."
