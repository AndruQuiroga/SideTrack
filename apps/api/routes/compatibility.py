"""Compatibility stub endpoint.

Implements GET /users/{user_a}/compatibility/{user_b} returning a simple score with overlap details.
"""

from __future__ import annotations

from fastapi import APIRouter, Path

router = APIRouter(prefix="/users", tags=["compatibility"])


@router.get("/{user_a}/compatibility/{user_b}")
async def get_compatibility(
    user_a: str = Path(..., description="User A ID"),
    user_b: str = Path(..., description="User B ID"),
) -> dict[str, object]:
    # Demo logic: deterministic but fake score based on IDs
    score = (sum(ord(c) for c in (user_a + user_b)) % 51) + 50  # 50..100
    overlap = {
        "shared_artists": ["Bjork", "Little Simz", "Radiohead"],
        "shared_genres": ["Art Pop", "Indie Rock", "Alt Hip-Hop"],
    }
    explanation = "Similarity based on shared artists, genres, and mood/energy proximity (demo)."
    return {"score": score, "overlap": overlap, "explanation": explanation}
