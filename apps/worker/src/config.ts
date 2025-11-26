import { ProviderType } from '@sidetrack/shared';

export interface ProviderConfig {
  provider: ProviderType;
  enabled: boolean;
}

export interface WorkerConfig {
  apiBaseUrl: string;
  apiToken?: string;
  syncIntervalMs: number;
  nowPlayingIntervalMs: number;
  enableNowPlaying: boolean;
  providers: ProviderConfig[];
}

const minutes = (value: number) => value * 60 * 1000;

export function loadConfig(): WorkerConfig {
  const providerEnvs: ProviderConfig[] = [
    {
      provider: ProviderType.SPOTIFY,
      enabled: process.env.WORKER_ENABLE_SPOTIFY !== 'false',
    },
    {
      provider: ProviderType.LASTFM,
      enabled: process.env.WORKER_ENABLE_LASTFM !== 'false',
    },
    {
      provider: ProviderType.LISTENBRAINZ,
      enabled: process.env.WORKER_ENABLE_LISTENBRAINZ !== 'false',
    },
  ];

  const syncMinutes = Number(process.env.WORKER_SYNC_INTERVAL_MINUTES ?? '15');
  const nowPlayingSeconds = Number(process.env.WORKER_NOW_PLAYING_SECONDS ?? '45');

  return {
    apiBaseUrl: process.env.SIDETRACK_API_BASE_URL ?? 'http://localhost:8000',
    apiToken: process.env.SIDETRACK_API_TOKEN,
    syncIntervalMs: minutes(Number.isFinite(syncMinutes) ? syncMinutes : 15),
    nowPlayingIntervalMs: (Number.isFinite(nowPlayingSeconds) ? nowPlayingSeconds : 45) * 1000,
    enableNowPlaying: process.env.WORKER_ENABLE_NOW_PLAYING !== 'false',
    providers: providerEnvs,
  };
}
