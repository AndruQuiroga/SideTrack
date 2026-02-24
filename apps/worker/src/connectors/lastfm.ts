import {
  LinkedAccountRead,
  ListenSource,
  ProviderType,
  SidetrackApiClient,
} from '@sidetrack/shared';

import { NormalizedListen, ProviderConnector } from './base';

export class LastfmConnector implements ProviderConnector {
  provider = ProviderType.LASTFM;
  source = ListenSource.LASTFM;

  constructor(private readonly client: SidetrackApiClient) {}

  async refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead> {
    // Last.fm uses session keys (non-expiring) — no token refresh needed.
    return account;
  }

  /**
   * Delegates to the API's POST /ingest/lastfm endpoint which fetches and
   * stores scrobbles server-side. Returns an empty list because the API
   * already handled persistence; the worker's store.upsert call becomes a
   * no-op.
   */
  async fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]> {
    const sinceTs = since ? Math.floor(since.getTime() / 1000) : undefined;
    try {
      const result = await this.client.ingestLastfm(
        account.user_id,
        account.provider_user_id,
        sinceTs,
      );
      console.info(
        `[lastfm] Ingested ${result.inserted} listens for user ${account.user_id} (last_ts=${result.last_ts})`,
      );
    } catch (error) {
      console.error('[lastfm] Ingest failed', {
        user_id: account.user_id,
        error: error instanceof Error ? error.message : String(error),
      });
    }
    // API handled persistence; return empty so store.upsert is a no-op.
    return [];
  }

  async fetchNowPlaying(account: LinkedAccountRead): Promise<NormalizedListen | null> {
    // Last.fm now-playing is handled via the API's /users/{id}/listening/now-playing
    // endpoint which reads from the DB. Return null to avoid double-counting.
    return null;
  }
}
