import { LinkedAccountRead, ListenSource, ProviderType } from '@sidetrack/shared';

export interface NormalizedListen {
  trackExternalId: string;
  playedAt: Date;
  metadata?: Record<string, unknown>;
}

export interface ProviderConnector {
  provider: ProviderType;
  source: ListenSource;
  refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead>;
  fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]>;
  fetchNowPlaying?(account: LinkedAccountRead): Promise<NormalizedListen | null>;
}
