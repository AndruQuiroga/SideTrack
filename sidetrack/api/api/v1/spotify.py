from fastapi import APIRouter, Depends

from ...clients.spotify import SpotifyClient, get_spotify_client
from ...config import Settings, get_settings
from ...schemas.listens import IngestResponse
from ...security import get_current_user
from ...services.spotify_service import SpotifyService, get_spotify_service

router = APIRouter()


@router.post("/spotify/listens", response_model=IngestResponse)
async def import_spotify_listens(
    spotify_service: SpotifyService = Depends(get_spotify_service),
    spotify_client: SpotifyClient = Depends(get_spotify_client),
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user),
):
    token = settings.spotify_token
    if not token:
        return IngestResponse(detail="missing token", ingested=0, source="spotify")
    items = await spotify_client.fetch_recently_played(token)
    created = await spotify_service.ingest_recently_played(items, user_id)
    return IngestResponse(detail="ok", ingested=created, source="spotify")
