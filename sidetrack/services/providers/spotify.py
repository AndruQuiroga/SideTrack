"""Spotify ingestion backend."""

from __future__ import annotations

from typing import Any, List


class SpotifyIngester:
    """Fetch listens from the Spotify API.

    This class currently serves as a placeholder for future integration.  It
    exposes a :meth:`fetch_recent` method that should be implemented with real
    Spotify API calls.
    """

    def fetch_recent(self, user_token: str, since: float | None = None) -> List[dict[str, Any]]:
        """Return recent listens for a user.

        Parameters
        ----------
        user_token:
            OAuth access token for the user.
        since:
            Optional unix timestamp for the earliest listen to return.
        """
        raise NotImplementedError
