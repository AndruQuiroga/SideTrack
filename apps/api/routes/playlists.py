"""Playlist stub endpoints.

Implements POST /playlist/blend to create a blended playlist preview for two users.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/playlist", tags=["playlists"])


class BlendRequest(BaseModel):
    user_a: str
    user_b: str


@router.post("/blend")
async def create_blend(payload: BlendRequest) -> dict[str, object]:
    tracks = [
        {"id": "t1", "title": "Shared Favorite", "artist_name": "The Pair", "reason": "shared artist"},
        {"id": "t2", "title": "Vibe Match", "artist_name": "Mood Duo", "reason": "energy/valence blend"},
        {"id": "t3", "title": "Wild Card", "artist_name": "Curveball", "reason": "explore zone"},
    ]
    return {
        "name": f"Friend Blend: {payload.user_a} + {payload.user_b}",
        "description": "A quick blend based on compatibility (demo)",
        "tracks": tracks,
    }
