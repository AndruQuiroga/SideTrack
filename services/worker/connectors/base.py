"""Base types and interface for provider connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from services.api.models import LinkedAccount, ProviderType
from services.api.models.listening import ListenSource


@dataclass
class NormalizedListen:
    """A provider-agnostic listen event."""

    track_external_id: str
    played_at: datetime
    metadata: dict[str, str | bool | None] = field(default_factory=dict)


class ProviderConnector(Protocol):
    """Interface that each provider connector must implement."""

    provider: ProviderType
    source: ListenSource

    async def refresh_access_token(self, account: LinkedAccount) -> LinkedAccount:
        """Refresh the account's access token if needed. Returns the (possibly updated) account."""
        ...

    async def fetch_recent(
        self, account: LinkedAccount, since: datetime | None = None
    ) -> list[NormalizedListen]:
        """Fetch recent listens for the given account."""
        ...

    async def fetch_now_playing(self, account: LinkedAccount) -> NormalizedListen | None:
        """Fetch the currently playing track, or None."""
        ...
