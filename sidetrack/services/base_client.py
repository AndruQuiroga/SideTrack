from __future__ import annotations

"""Abstract base client for music service integrations."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any


class MusicServiceClient(ABC):
    """Common interface for external music service clients."""

    source: str

    @abstractmethod
    def auth_url(self, callback: str) -> str:
        """Return an OAuth authorization URL for this service."""

    @abstractmethod
    async def fetch_recently_played(
        self, since: datetime | date | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch recently played items for the configured user."""
