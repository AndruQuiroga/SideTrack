from pydantic import BaseModel


class MusicbrainzIngestResponse(BaseModel):
    detail: str
    artist_id: int | None = None
    release_id: int
    tracks: int
