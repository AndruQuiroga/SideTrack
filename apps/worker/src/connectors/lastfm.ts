import { LinkedAccountRead, ListenSource, ProviderType } from '@sidetrack/shared';

import { NormalizedListen, ProviderConnector } from './base';

export class LastfmConnector implements ProviderConnector {
  provider = ProviderType.LASTFM;
  source = ListenSource.LASTFM;

  async refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead> {
    return {
      ...account,
      access_token: account.access_token ?? 'lastfm-session-key',
      token_expires_at: account.token_expires_at ?? null,
    };
  }

  async fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]> {
    const listens: NormalizedListen[] = [
      {
        trackExternalId: `${account.provider_user_id}-lastfm-track-a`,
        playedAt: new Date(Date.now() - 10 * 60 * 1000),
        metadata: { source: 'scrobble' },
      },
      {
        trackExternalId: `${account.provider_user_id}-lastfm-track-b`,
        playedAt: new Date(Date.now() - 65 * 60 * 1000),
        metadata: { source: 'scrobble' },
      },
    ];

    if (!since) return listens;
    return listens.filter((listen) => listen.playedAt.getTime() > since.getTime());
  }

  async fetchNowPlaying(account: LinkedAccountRead): Promise<NormalizedListen | null> {
    return {
      trackExternalId: `${account.provider_user_id}-lastfm-now`,
      playedAt: new Date(),
      metadata: { nowPlaying: true, service: 'lastfm' },
    };
  }
}
