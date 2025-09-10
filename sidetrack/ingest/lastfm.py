"""Last.fm ingestion backend."""

from __future__ import annotations

from typing import Any, List


class LastfmIngester:
    """Fetch listens from the Last.fm API.

    Actual API integration is not yet implemented; this class documents the
    intended interface for a Last.fm ingestion backend.
    """

    def fetch_recent(self, user: str, api_key: str, since: float | None = None) -> List[dict[str, Any]]:
        """Return recent listens for ``user``.

        Parameters
        ----------
        user:
            Last.fm username.
        api_key:
            Auth session key for the user.
        since:
            Optional unix timestamp for the earliest listen to return.
        """
        raise NotImplementedError
