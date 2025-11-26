import { LinkedAccountRead, ListenSource, ProviderType } from '@sidetrack/shared';

import { NormalizedListen, ProviderConnector } from './base';

function fakePlayedAt(offsetMinutes: number): Date {
  return new Date(Date.now() - offsetMinutes * 60 * 1000);
}

export class SpotifyConnector implements ProviderConnector {
  provider = ProviderType.SPOTIFY;
  source = ListenSource.SPOTIFY;

  async refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead> {
    const refreshedAt = new Date();
    const newExpiry = new Date(refreshedAt.getTime() + 55 * 60 * 1000);

    return {
      ...account,
      access_token: account.access_token ?? 'refreshed-spotify-token',
      token_expires_at: newExpiry.toISOString(),
    };
  }

  async fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]> {
    const baseListens: NormalizedListen[] = [
      {
        trackExternalId: `${account.provider_user_id}-spotify-track-1`,
        playedAt: fakePlayedAt(5),
        metadata: { context: 'recently played', provider: 'spotify' },
      },
      {
        trackExternalId: `${account.provider_user_id}-spotify-track-2`,
        playedAt: fakePlayedAt(25),
        metadata: { context: 'recently played', provider: 'spotify' },
      },
    ];

    if (!since) return baseListens;
    return baseListens.filter((listen) => listen.playedAt.getTime() > since.getTime());
  }

  async fetchNowPlaying(account: LinkedAccountRead): Promise<NormalizedListen | null> {
    const now = new Date();
    return {
      trackExternalId: `${account.provider_user_id}-spotify-now`,
      playedAt: now,
      metadata: { live: true, provider: 'spotify' },
    };
  }
}
