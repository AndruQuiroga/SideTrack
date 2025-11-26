import { LinkedAccountRead, ListenSource, ProviderType } from '@sidetrack/shared';

import { NormalizedListen, ProviderConnector } from './base';

export class ListenbrainzConnector implements ProviderConnector {
  provider = ProviderType.LISTENBRAINZ;
  source = ListenSource.LISTENBRAINZ;

  async refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead> {
    return {
      ...account,
      access_token: account.access_token ?? 'listenbrainz-token',
      token_expires_at: account.token_expires_at ?? null,
    };
  }

  async fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]> {
    const listens: NormalizedListen[] = [
      {
        trackExternalId: `${account.provider_user_id}-lb-track-1`,
        playedAt: new Date(Date.now() - 15 * 60 * 1000),
        metadata: { submission: 'playing_now' },
      },
      {
        trackExternalId: `${account.provider_user_id}-lb-track-2`,
        playedAt: new Date(Date.now() - 90 * 60 * 1000),
        metadata: { submission: 'imported' },
      },
    ];

    if (!since) return listens;
    return listens.filter((listen) => listen.playedAt.getTime() > since.getTime());
  }

  async fetchNowPlaying(account: LinkedAccountRead): Promise<NormalizedListen | null> {
    return {
      trackExternalId: `${account.provider_user_id}-lb-now`,
      playedAt: new Date(),
      metadata: { live: true, service: 'listenbrainz' },
    };
  }
}
