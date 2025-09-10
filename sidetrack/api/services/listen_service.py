from datetime import datetime

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..repositories.artist_repository import ArtistRepository
from ..repositories.listen_repository import ListenRepository
from ..repositories.release_repository import ReleaseRepository
from ..repositories.track_repository import TrackRepository
from ..utils import mb_sanitize


class ListenService:
    """Service layer handling listen ingestion."""

    def __init__(
        self,
        artist_repo: ArtistRepository,
        release_repo: ReleaseRepository,
        track_repo: TrackRepository,
        listen_repo: ListenRepository,
    ):
        self.artists = artist_repo
        self.releases = release_repo
        self.tracks = track_repo
        self.listens = listen_repo

    async def ingest_lb_rows(self, listens: list[dict], user_id: str | None = None) -> int:
        """Ingest ListenBrainz-style listen rows into the database."""
        created = 0
        for item in listens:
            tm = item.get("track_metadata", {})
            artist_name = (
                mb_sanitize(tm.get("artist_name") or tm.get("artist_name_mb")) or "Unknown"
            )
            track_title = mb_sanitize(tm.get("track_name")) or "Unknown"
            release_title = mb_sanitize(tm.get("release_name"))
            recording_mbid = (tm.get("mbid_mapping") or {}).get("recording_mbid")
            played_at_ts = item.get("listened_at")
            if not played_at_ts:
                continue
            played_at = datetime.utcfromtimestamp(played_at_ts)
            uid = (user_id or item.get("user_name") or "lb").lower()

            artist = await self.artists.get_or_create(name=artist_name)
            rel = None
            if release_title:
                rel = await self.releases.get_or_create(
                    title=release_title, artist_id=artist.artist_id
                )
            track = await self.tracks.get_or_create(
                mbid=recording_mbid,
                title=track_title,
                artist_id=artist.artist_id,
                release_id=rel.release_id if rel else None,
            )
            if not await self.listens.exists(uid, track.track_id, played_at):
                await self.listens.add(uid, track.track_id, played_at, "listenbrainz")
                created += 1
        await self.listens.commit()
        return created

    async def ingest_spotify_rows(self, items: list[dict], user_id: str) -> int:
        """Ingest Spotify ``recently played`` items.

        The input is expected to be in the format returned by
        :meth:`SpotifyClient.fetch_recently_played`.  This method converts each
        item into the ListenBrainz-style dictionary and delegates to
        :meth:`ingest_lb_rows`.
        """

        rows: list[dict] = []
        for item in items:
            track_data = item.get("track") or {}
            artist_name = (track_data.get("artists") or [{}])[0].get("name")
            title = track_data.get("name")
            played_at = datetime.fromisoformat(item.get("played_at", "").replace("Z", "+00:00"))
            rows.append(
                {
                    "track_metadata": {
                        "artist_name": artist_name,
                        "track_name": title,
                        "mbid_mapping": {"recording_mbid": track_data.get("mbid")},
                    },
                    "listened_at": int(played_at.timestamp()),
                    "user_name": user_id,
                }
            )
        return await self.ingest_lb_rows(rows, user_id)

    async def ingest_lastfm_rows(self, tracks: list[dict], user_id: str) -> int:
        """Ingest Last.fm ``recenttracks`` data."""

        rows: list[dict] = []
        for item in tracks:
            artist = (item.get("artist") or {}).get("#text") or item.get("artist")
            title = item.get("name") or item.get("track")
            ts = item.get("date", {}).get("uts") or item.get("uts")
            try:
                listened_at = int(ts)
            except (TypeError, ValueError):
                continue
            rows.append(
                {
                    "track_metadata": {
                        "artist_name": artist,
                        "track_name": title,
                    },
                    "listened_at": listened_at,
                    "user_name": user_id,
                }
            )
        return await self.ingest_lb_rows(rows, user_id)


def get_listen_service(db: AsyncSession = Depends(get_db)) -> ListenService:
    """FastAPI dependency that provides a :class:`ListenService` instance."""
    artist_repo = ArtistRepository(db)
    release_repo = ReleaseRepository(db)
    track_repo = TrackRepository(db)
    listen_repo = ListenRepository(db)
    return ListenService(artist_repo, release_repo, track_repo, listen_repo)
