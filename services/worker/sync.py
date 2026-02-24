"""Sync coordinator — orchestrates periodic data fetching from all providers.

Replaces the TS SyncCoordinator. Operates directly against the database
instead of making HTTP calls to the API.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy.orm import Session

from services.api.models import LinkedAccount, ProviderType, User
from services.api.models.listening import ListenSource

from .connectors.base import ProviderConnector
from .listen_store import ListenEventStore

logger = logging.getLogger(__name__)


class SyncCoordinator:
    """Orchestrates sync cycles across all users and providers."""

    def __init__(
        self,
        store: ListenEventStore,
        connectors: Mapping[ProviderType, ProviderConnector],
        disabled_providers: set[ProviderType] | None = None,
    ) -> None:
        self.store = store
        self.connectors = connectors
        self.disabled_providers = disabled_providers or set()

        # Per user:source cursor tracking
        self._cursors: dict[str, datetime] = {}

        # Simple metrics counters
        self.metrics: dict[str, dict] = {}

    def _cursor_key(self, user_id: uuid.UUID, source: ListenSource) -> str:
        return f"{user_id}:{source.value}"

    def _record_success(self, scope: str) -> None:
        m = self.metrics.setdefault(scope, {"successes": 0, "failures": 0})
        m["successes"] += 1
        m["last_sync_at"] = datetime.utcnow().isoformat()

    def _record_error(self, scope: str, error: Exception) -> None:
        m = self.metrics.setdefault(scope, {"successes": 0, "failures": 0})
        m["failures"] += 1
        m["last_error"] = str(error)

    # ── Full sync ──────────────────────────────────────────────────

    async def run_full_sync(self, db: Session) -> None:
        """Iterate all users and their linked accounts, fetching recent listens."""
        users = list(db.query(User).all())
        for user in users:
            accounts = list(db.query(LinkedAccount).filter(LinkedAccount.user_id == user.id).all())
            for account in accounts:
                await self._sync_account(db, user, account)

    async def _sync_account(self, db: Session, user: User, account: LinkedAccount) -> None:
        connector = self.connectors.get(account.provider)
        if not connector:
            return
        if account.provider in self.disabled_providers:
            return

        key = self._cursor_key(user.id, connector.source)
        since = self._cursors.get(key)

        try:
            refreshed = await connector.refresh_access_token(account)
            # Persist refreshed tokens
            if refreshed.access_token != account.access_token:
                db.add(refreshed)
                db.commit()

            listens = await connector.fetch_recent(refreshed, since)
            result = self.store.upsert(db, user.id, connector.source, listens, refreshed)

            if result.last_played_at:
                self._cursors[key] = result.last_played_at

            self._record_success(key)
        except Exception as exc:
            logger.exception(
                "Failed to sync account user=%s provider=%s", user.id, account.provider
            )
            self._record_error(key, exc)

    # ── Now-playing sweep ──────────────────────────────────────────

    async def run_now_playing_sweep(self, db: Session) -> None:
        """Check now-playing for all users with capable connectors."""
        users = list(db.query(User).all())
        for user in users:
            accounts = list(db.query(LinkedAccount).filter(LinkedAccount.user_id == user.id).all())
            for account in accounts:
                connector = self.connectors.get(account.provider)
                if not connector:
                    continue
                if account.provider in self.disabled_providers:
                    continue
                if not hasattr(connector, "fetch_now_playing"):
                    continue

                try:
                    refreshed = await connector.refresh_access_token(account)
                    if refreshed.access_token != account.access_token:
                        db.add(refreshed)
                        db.commit()

                    now_playing = await connector.fetch_now_playing(refreshed)
                    if not now_playing:
                        continue

                    self.store.upsert(db, user.id, connector.source, [now_playing], refreshed)
                    self._record_success(f"{user.id}:{connector.source.value}:now")
                except Exception as exc:
                    logger.exception(
                        "Now-playing sweep failed user=%s provider=%s",
                        user.id,
                        account.provider,
                    )
                    self._record_error(f"{user.id}:{account.provider}:now", exc)

    # ── Status ─────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return current sync status for the health endpoint."""
        return {
            "metrics": self.metrics,
            "cursors": {k: v.isoformat() for k, v in self._cursors.items()},
        }
