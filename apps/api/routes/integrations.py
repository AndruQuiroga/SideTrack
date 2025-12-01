"""Stub integration endpoints for Spotify/Last.fm/Discord connect flows.

These endpoints are placeholders to enable frontend wiring and can be
replaced with real OAuth flows later.
"""

from __future__ import annotations

from fastapi import APIRouter, Path

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/{provider}/connect")
async def connect_integration(
    provider: str = Path(..., pattern="^(spotify|lastfm|discord)$", description="Integration provider"),
) -> dict[str, str]:
    redirect_map = {
        "spotify": "https://accounts.spotify.com/authorize?client_id=demo&response_type=code",
        "lastfm": "https://www.last.fm/api/auth/?api_key=demo",
        "discord": "https://discord.com/oauth2/authorize?client_id=demo&response_type=code",
    }
    return {"status": "ok", "url": redirect_map.get(provider, "https://example.com/")}
