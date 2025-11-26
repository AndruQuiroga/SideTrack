import crypto from 'crypto';

import {
  LinkedAccountRead,
  ListenEventCreate,
  ListenSource,
  SidetrackApiClient,
  UUID,
} from '@sidetrack/shared';

import { NormalizedListen } from './connectors/base';
import { MetricsRegistry } from './metrics';

const UUID_PATTERN = /(.{8})(.{4})(.{4})(.{4})(.{12})/;

function deterministicUuid(input: string): UUID {
  const hash = crypto.createHash('sha1').update(input).digest('hex').slice(0, 32);
  return hash.replace(UUID_PATTERN, '$1-$2-$3-$4-$5');
}

export interface ListenIngestResult {
  ingested: number;
  skipped: number;
  lastPlayedAt?: Date;
}

export class ListenEventStore {
  private readonly apiClient: SidetrackApiClient;
  private readonly metrics: MetricsRegistry;
  private readonly dedupeKeys = new Set<string>();

  constructor(apiClient: SidetrackApiClient, metrics: MetricsRegistry) {
    this.apiClient = apiClient;
    this.metrics = metrics;
  }

  async upsert(
    userId: UUID,
    source: ListenSource,
    listens: NormalizedListen[],
    account: LinkedAccountRead,
  ): Promise<ListenIngestResult> {
    const payload: ListenEventCreate[] = [];
    for (const listen of listens) {
      const trackUuid = deterministicUuid(`${source}:${listen.trackExternalId}`);
      const playedAt = listen.playedAt.toISOString();
      const key = `${userId}:${trackUuid}:${playedAt}`;
      if (this.dedupeKeys.has(key)) {
        this.metrics.recordDeduped();
        continue;
      }

      payload.push({
        user_id: userId,
        track_id: trackUuid,
        played_at: playedAt,
        source,
        metadata: { ...listen.metadata, provider_user_id: account.provider_user_id },
      });
      this.dedupeKeys.add(key);
    }

    if (payload.length === 0) {
      return { ingested: 0, skipped: listens.length };
    }

    try {
      await this.apiClient.upsertListenEvents(payload);
      this.metrics.recordListenIngest(payload.length);
      const firstListen = listens.length > 0 ? listens[0] : undefined;
      return { ingested: payload.length, skipped: listens.length - payload.length, lastPlayedAt: firstListen?.playedAt };
    } catch (error) {
      this.metrics.recordError('listen_ingest');
      // Keep dedupe entries but surface the error so the caller can log it.
      throw error;
    }
  }
}
