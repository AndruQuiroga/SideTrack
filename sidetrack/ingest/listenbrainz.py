"""ListenBrainz ingestion backend."""

from __future__ import annotations

from typing import Any, List


class ListenBrainzIngester:
    """Fetch listens from the ListenBrainz API."""

    def fetch_recent(self, user: str, token: str | None = None, since: float | None = None) -> List[dict[str, Any]]:
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
        raise NotImplementedError
