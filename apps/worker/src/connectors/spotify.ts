import { LinkedAccountRead, ListenSource, ProviderType } from '@sidetrack/shared';

import { NormalizedListen, ProviderConnector } from './base';

const SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token';
const SPOTIFY_RECENT_URL = 'https://api.spotify.com/v1/me/player/recently-played';
const SPOTIFY_NOW_PLAYING_URL = 'https://api.spotify.com/v1/me/player/currently-playing';

export class SpotifyConnector implements ProviderConnector {
  provider = ProviderType.SPOTIFY;
  source = ListenSource.SPOTIFY;

  private readonly clientId: string | undefined;
  private readonly clientSecret: string | undefined;

  constructor(
    clientId = process.env.SPOTIFY_CLIENT_ID,
    clientSecret = process.env.SPOTIFY_CLIENT_SECRET,
  ) {
    this.clientId = clientId;
    this.clientSecret = clientSecret;
  }

  async refreshAccessToken(account: LinkedAccountRead): Promise<LinkedAccountRead> {
    if (!this.clientId || !this.clientSecret || !account.refresh_token) {
      return account;
    }

    try {
      const credentials = Buffer.from(`${this.clientId}:${this.clientSecret}`).toString('base64');
      const res = await fetch(SPOTIFY_TOKEN_URL, {
        method: 'POST',
        headers: {
          Authorization: `Basic ${credentials}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          refresh_token: account.refresh_token,
        }),
      });

      if (!res.ok) return account;

      const data = (await res.json()) as {
        access_token: string;
        expires_in: number;
        refresh_token?: string;
      };

      return {
        ...account,
        access_token: data.access_token,
        token_expires_at: new Date(Date.now() + data.expires_in * 1000).toISOString(),
        ...(data.refresh_token ? { refresh_token: data.refresh_token } : {}),
      };
    } catch {
      return account;
    }
  }

  async fetchRecent(account: LinkedAccountRead, since?: Date): Promise<NormalizedListen[]> {
    if (!account.access_token) return [];

    try {
      const params = new URLSearchParams({ limit: '50' });
      if (since) params.set('after', String(since.getTime()));

      const res = await fetch(`${SPOTIFY_RECENT_URL}?${params}`, {
        headers: { Authorization: `Bearer ${account.access_token}` },
      });

      if (!res.ok) return [];

      const data = (await res.json()) as {
        items: Array<{
          track: {
            id: string;
            name: string;
            artists: Array<{ name: string }>;
            album: { name: string };
          };
          played_at: string;
        }>;
      };

      return (data.items ?? []).map((item) => ({
        trackExternalId: item.track.id,
        playedAt: new Date(item.played_at),
        metadata: {
          track_name: item.track.name,
          artist_name: item.track.artists[0]?.name,
          album_name: item.track.album?.name,
          provider: 'spotify',
        },
      }));
    } catch {
      return [];
    }
  }

  async fetchNowPlaying(account: LinkedAccountRead): Promise<NormalizedListen | null> {
    if (!account.access_token) return null;

    try {
      const res = await fetch(SPOTIFY_NOW_PLAYING_URL, {
        headers: { Authorization: `Bearer ${account.access_token}` },
      });

      if (!res.ok || res.status === 204) return null;

      const data = (await res.json()) as {
        is_playing: boolean;
        item: { id: string; name: string; artists: Array<{ name: string }> } | null;
      };

      if (!data.is_playing || !data.item) return null;

      return {
        trackExternalId: data.item.id,
        playedAt: new Date(),
        metadata: {
          track_name: data.item.name,
          artist_name: data.item.artists[0]?.name,
          live: true,
          provider: 'spotify',
        },
      };
    } catch {
      return null;
    }
  }

  /** Obtain a client credentials token for non-user Spotify API calls (e.g. audio features). */
  async getClientToken(): Promise<string | null> {
    if (!this.clientId || !this.clientSecret) return null;

    try {
      const credentials = Buffer.from(`${this.clientId}:${this.clientSecret}`).toString('base64');
      const res = await fetch(SPOTIFY_TOKEN_URL, {
        method: 'POST',
        headers: {
          Authorization: `Basic ${credentials}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ grant_type: 'client_credentials' }),
      });

      if (!res.ok) return null;
      const data = (await res.json()) as { access_token: string };
      return data.access_token;
    } catch {
      return null;
    }
  }
}
