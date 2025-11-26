import {
  LinkedAccountRead,
  ListenSource,
  ProviderType,
  SidetrackApiClient,
  UserRead,
  UUID,
} from '@sidetrack/shared';

import { ProviderConnector } from './connectors/base';
import { ListenbrainzConnector } from './connectors/listenbrainz';
import { LastfmConnector } from './connectors/lastfm';
import { SpotifyConnector } from './connectors/spotify';
import { ListenEventStore } from './listenEvents';
import { MetricsRegistry, MetricsSnapshot } from './metrics';

interface SyncStateEntry {
  lastSyncedAt?: Date;
}

export interface SyncStatus {
  metrics: MetricsSnapshot;
  cursors: Record<string, string | undefined>;
}

export class SyncCoordinator {
  private readonly client: SidetrackApiClient;
  private readonly store: ListenEventStore;
  private readonly metrics: MetricsRegistry;
  private readonly connectors: Map<ProviderType, ProviderConnector>;
  private readonly syncState: Map<string, SyncStateEntry> = new Map();
  private readonly disabledProviders: Set<ProviderType>;

  constructor(
    client: SidetrackApiClient,
    store: ListenEventStore,
    metrics: MetricsRegistry,
    disabledProviders: ProviderType[],
  ) {
    this.client = client;
    this.store = store;
    this.metrics = metrics;
    this.connectors = new Map<ProviderType, ProviderConnector>();
    this.disabledProviders = new Set(disabledProviders);
    this.registerConnectors();
  }

  async runFullSync(): Promise<void> {
    const users = await this.client.listUsers();
    for (const user of users) {
      const accounts = await this.client.listLinkedAccounts(user.id);
      for (const account of accounts) {
        await this.syncAccount(user, account);
      }
    }
  }

  async runNowPlayingSweep(): Promise<void> {
    const users = await this.client.listUsers();
    for (const user of users) {
      const accounts = await this.client.listLinkedAccounts(user.id);
      for (const account of accounts) {
        const connector = this.connectors.get(account.provider as ProviderType);
        if (!connector || typeof connector.fetchNowPlaying !== 'function') continue;
        if (this.disabledProviders.has(account.provider as ProviderType)) continue;

        try {
          const refreshed = await connector.refreshAccessToken(account);
          const nowPlaying = await connector.fetchNowPlaying?.(refreshed);
          if (!nowPlaying) continue;
          await this.store.upsert(user.id, connector.source, [nowPlaying], refreshed);
          this.metrics.recordSuccess(`${user.id}:${connector.source}:now`);
        } catch (error) {
          console.error('Failed now-playing sweep', { user: user.id, provider: account.provider, error });
          this.metrics.recordError(`${user.id}:${account.provider}:now`, error);
        }
      }
    }
  }

  status(): SyncStatus {
    const cursors: Record<string, string | undefined> = {};
    this.syncState.forEach((entry, key) => {
      cursors[key] = entry.lastSyncedAt?.toISOString();
    });
    return {
      metrics: this.metrics.snapshot(),
      cursors,
    };
  }

  private registerConnectors(): void {
    const connectors: ProviderConnector[] = [new SpotifyConnector(), new LastfmConnector(), new ListenbrainzConnector()];
    for (const connector of connectors) {
      this.connectors.set(connector.provider, connector);
    }
  }

  private async syncAccount(user: UserRead, account: LinkedAccountRead): Promise<void> {
    const connector = this.connectors.get(account.provider as ProviderType);
    if (!connector) return;
    if (this.disabledProviders.has(account.provider as ProviderType)) return;

    const key = this.cursorKey(user.id, connector.source);
    const since = this.syncState.get(key)?.lastSyncedAt;
    try {
      const refreshed = await connector.refreshAccessToken(account);
      const listens = await connector.fetchRecent(refreshed, since);
      const result = await this.store.upsert(user.id, connector.source, listens, refreshed);
      if (result.lastPlayedAt) {
        this.syncState.set(key, { lastSyncedAt: result.lastPlayedAt });
      }
      this.metrics.recordSuccess(key);
    } catch (error) {
      console.error('Failed to sync account', { user: user.id, provider: account.provider, error });
      this.metrics.recordError(key, error);
    }
  }

  private cursorKey(userId: UUID, source: ListenSource): string {
    return `${userId}:${source}`;
  }
}
