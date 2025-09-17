"""ListenBrainz ingestion backend."""

from __future__ import annotations

from typing import Any, List

import httpx

from sidetrack.services.listenbrainz import ListenBrainzClient


class _ProviderListenBrainzClient(ListenBrainzClient):
    """Concrete ListenBrainz client for ingestion purposes."""

    def auth_url(self, callback: str) -> str:  # pragma: no cover - CLI usage
        raise NotImplementedError("ListenBrainz token auth is handled externally")


class ListenBrainzIngester:
    """Fetch listens from the ListenBrainz API."""

    def __init__(self, *, page_size: int = 500) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        # ListenBrainz caps count at 1000 per request.
        self.page_size = min(page_size, 1000)

    async def fetch_recent(
        self,
        user: str,
        token: str | None = None,
        since: float | None = None,
    ) -> List[dict[str, Any]]:
        """Return recent listens for ``user``.

        Parameters
        ----------
        user:
            ListenBrainz username.
        token:
            Optional token for authenticated requests.
        since:
            Optional unix timestamp for the earliest listen to return.
        """

        headers = {"Authorization": f"Token {token}"} if token else None
        min_ts = int(since) + 1 if since is not None else None
        listens: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            lb_client = _ProviderListenBrainzClient(client)
            base_url = f"{lb_client.base_url}/user/{user}/listens"
            url: str | None = base_url
            params: dict[str, Any] | None = {"count": self.page_size}
            sticky_params: dict[str, Any] | None = {"min_ts": min_ts} if min_ts else None

            while url:
                if params and min_ts is not None:
                    params["min_ts"] = min_ts

                resp = await lb_client._get(url, params=params, headers=headers)
                data = resp.json()
                raw_listens, cursor = ListenBrainzClient._extract_listens_payload(data)

                if not raw_listens:
                    break

                oldest_ts: int | None = None
                for raw in raw_listens:
                    if not isinstance(raw, dict):
                        continue
                    raw_ts = raw.get("listened_at")
                    if isinstance(raw_ts, (int, float)):
                        ts = int(raw_ts)
                        if oldest_ts is None or ts < oldest_ts:
                            oldest_ts = ts
                    normalised = self._normalise_listen(raw, user)
                    if normalised is None:
                        continue
                    if since is not None and normalised["listened_at"] <= since:
                        continue
                    listens.append(normalised)

                if since is not None and oldest_ts is not None and oldest_ts <= since:
                    break

                url = ListenBrainzClient._prepare_next_url(
                    base_url,
                    cursor,
                    sticky_params=sticky_params,
                    default_count=self.page_size,
                )
                params = None

        return listens

    @staticmethod
    def _normalise_listen(listen: dict[str, Any], user: str) -> dict[str, Any] | None:
        """Convert a ListenBrainz payload row to a ListenService compatible dict."""

        listened_at = listen.get("listened_at")
        try:
            listened_at_int = int(listened_at)
        except (TypeError, ValueError):
            return None

        raw_metadata = listen.get("track_metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}

        if "track_name" not in metadata and metadata.get("title"):
            metadata["track_name"] = metadata.get("title")
        if "artist_name" not in metadata and metadata.get("artist"):
            metadata["artist_name"] = metadata.get("artist")

        mbid_mapping = metadata.get("mbid_mapping")
        if not isinstance(mbid_mapping, dict):
            mbid_mapping = None

        recording_mbid = None
        if mbid_mapping:
            recording_mbid = mbid_mapping.get("recording_mbid")

        additional_info = metadata.get("additional_info")
        if recording_mbid is None and isinstance(additional_info, dict):
            recording_mbid = additional_info.get("recording_mbid")

        if recording_mbid:
            existing = mbid_mapping or {}
            metadata["mbid_mapping"] = {**existing, "recording_mbid": recording_mbid}
        elif mbid_mapping is not None:
            metadata["mbid_mapping"] = dict(mbid_mapping)

        return {
            "track_metadata": metadata,
            "listened_at": listened_at_int,
            "user_name": listen.get("user_name") or user,
        }
