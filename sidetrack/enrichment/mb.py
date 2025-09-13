from __future__ import annotations

import logging

import httpx

from sidetrack.services.musicbrainz import MusicBrainzService

from . import TrackRef


class MusicBrainzAdapter:
    """Simple wrapper for MusicBrainz lookups."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        headers = {"User-Agent": "SideTrack/0.1 (+https://example.com)"}
        self._client = client or httpx.AsyncClient(headers=headers)
        self._service = MusicBrainzService(self._client)

    logger = logging.getLogger(__name__)

    async def close(self) -> None:
        await self._client.aclose()

    async def recording_by_isrc(self, isrc: str) -> TrackRef | None:
        """Return basic metadata for a recording identified by its ISRC."""

        try:
            data = await self._service.recording_by_isrc(isrc)
            if not data.get("recording_mbid"):
                return None
            title = data.get("title") or ""
            artists = data.get("artists") or []
            mbid = data.get("recording_mbid")
            self.logger.info("enrichment_mb_success isrc=%s", isrc)
            return TrackRef(title=title, artists=artists, isrc=isrc, lastfm_mbid=mbid)
        except Exception as exc:  # pragma: no cover - error logging
            self.logger.warning("enrichment_mb_fail isrc=%s error=%s", isrc, str(exc))
            raise
