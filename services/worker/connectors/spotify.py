"""Spotify provider connector — token refresh, recent listens, now-playing, client credentials."""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime

import httpx

from services.api.models import LinkedAccount, ProviderType
from services.api.models.listening import ListenSource

from .base import NormalizedListen

logger = logging.getLogger(__name__)

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_RECENT_URL = "https://api.spotify.com/v1/me/player/recently-played"
SPOTIFY_NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"


class SpotifyConnector:
    """Handles all Spotify API interactions for the worker."""

    provider = ProviderType.SPOTIFY
    source = ListenSource.SPOTIFY

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._http = http_client or httpx.AsyncClient(timeout=30.0)

    @property
    def _basic_auth(self) -> str:
        """Base64-encoded client_id:client_secret for Basic auth."""
        raw = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(raw.encode()).decode()

    # ── Token management ───────────────────────────────────────────

    async def refresh_access_token(self, account: LinkedAccount) -> LinkedAccount:
        """Refresh the user's Spotify access token using the stored refresh_token."""
        if not self.client_id or not self.client_secret or not account.refresh_token:
            return account

        try:
            resp = await self._http.post(
                SPOTIFY_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {self._basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": account.refresh_token,
                },
            )
            if not resp.is_success:
                logger.warning("Spotify token refresh failed: %s", resp.status_code)
                return account

            data = resp.json()
            account.access_token = data["access_token"]
            account.token_expires_at = datetime.fromtimestamp(
                datetime.now(UTC).timestamp() + data["expires_in"],
                tz=UTC,
            )
            if "refresh_token" in data:
                account.refresh_token = data["refresh_token"]
            return account
        except Exception:
            logger.exception("Spotify token refresh error")
            return account

    async def get_client_token(self) -> str | None:
        """Obtain a client credentials token for non-user API calls (e.g. audio features)."""
        if not self.client_id or not self.client_secret:
            return None

        try:
            resp = await self._http.post(
                SPOTIFY_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {self._basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
            if not resp.is_success:
                return None
            data: dict = resp.json()
            return str(data["access_token"])
        except Exception:
            logger.exception("Spotify client credentials error")
            return None

    # ── Listening data ─────────────────────────────────────────────

    async def fetch_recent(
        self, account: LinkedAccount, since: datetime | None = None
    ) -> list[NormalizedListen]:
        """Fetch up to 50 recently played tracks for a user."""
        if not account.access_token:
            return []

        try:
            params: dict[str, str] = {"limit": "50"}
            if since:
                params["after"] = str(int(since.timestamp() * 1000))

            resp = await self._http.get(
                SPOTIFY_RECENT_URL,
                headers={"Authorization": f"Bearer {account.access_token}"},
                params=params,
            )
            if not resp.is_success:
                logger.warning("Spotify fetch-recent failed: %s", resp.status_code)
                return []

            data = resp.json()
            listens: list[NormalizedListen] = []
            for item in data.get("items", []):
                track = item["track"]
                artists = track.get("artists", [])
                listens.append(
                    NormalizedListen(
                        track_external_id=track["id"],
                        played_at=datetime.fromisoformat(item["played_at"].replace("Z", "+00:00")),
                        metadata={
                            "track_name": track.get("name"),
                            "artist_name": artists[0]["name"] if artists else None,
                            "album_name": track.get("album", {}).get("name"),
                            "provider": "spotify",
                        },
                    )
                )
            return listens
        except Exception:
            logger.exception("Spotify fetch-recent error")
            return []

    async def fetch_now_playing(self, account: LinkedAccount) -> NormalizedListen | None:
        """Fetch the user's currently playing track, or None."""
        if not account.access_token:
            return None

        try:
            resp = await self._http.get(
                SPOTIFY_NOW_PLAYING_URL,
                headers={"Authorization": f"Bearer {account.access_token}"},
            )
            if not resp.is_success or resp.status_code == 204:
                return None

            data = resp.json()
            if not data.get("is_playing") or not data.get("item"):
                return None

            item = data["item"]
            artists = item.get("artists", [])
            return NormalizedListen(
                track_external_id=item["id"],
                played_at=datetime.now(UTC),
                metadata={
                    "track_name": item.get("name"),
                    "artist_name": artists[0]["name"] if artists else None,
                    "live": True,
                    "provider": "spotify",
                },
            )
        except Exception:
            logger.exception("Spotify now-playing error")
            return None

    # ── Audio features ─────────────────────────────────────────────

    async def fetch_audio_features_batch(self, spotify_ids: list[str], token: str) -> list[dict]:
        """Fetch audio features for up to 100 Spotify track IDs.

        Returns a list of feature dicts (only non-null entries).
        """
        try:
            resp = await self._http.get(
                SPOTIFY_AUDIO_FEATURES_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"ids": ",".join(spotify_ids)},
            )
            if not resp.is_success:
                logger.warning("Spotify audio-features batch failed: %s", resp.status_code)
                return []

            data = resp.json()
            return [f for f in data.get("audio_features", []) if f is not None]
        except Exception:
            logger.exception("Spotify audio-features batch error")
            return []

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()
