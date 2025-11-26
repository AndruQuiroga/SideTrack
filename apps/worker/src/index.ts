import { SidetrackApiClient } from '@sidetrack/shared';

import { loadConfig } from './config';
import { ListenEventStore } from './listenEvents';
import { MetricsRegistry } from './metrics';
import { StatusServer } from './statusServer';
import { SyncCoordinator } from './sync';

export function startWorker(): void {
  const config = loadConfig();
  const metrics = new MetricsRegistry();
  const client = new SidetrackApiClient({ baseUrl: config.apiBaseUrl, authToken: config.apiToken });
  const store = new ListenEventStore(client, metrics);
  const disabledProviders = config.providers.filter((provider) => !provider.enabled).map((provider) => provider.provider);

  const coordinator = new SyncCoordinator(client, store, metrics, disabledProviders);
  const statusServer = new StatusServer(coordinator);
  statusServer.start();

  const runSync = async () => {
    try {
      await coordinator.runFullSync();
    } catch (error) {
      metrics.recordError('sync', error);
      console.error('[worker] periodic sync failed', error);
    }
  };

  void runSync();
  setInterval(runSync, config.syncIntervalMs);

  if (config.enableNowPlaying) {
    const runNowPlaying = async () => {
      try {
        await coordinator.runNowPlayingSweep();
      } catch (error) {
        metrics.recordError('now_playing', error);
        console.error('[worker] now-playing sweep failed', error);
      }
    };
    void runNowPlaying();
    setInterval(runNowPlaying, config.nowPlayingIntervalMs);
  }

  console.log('[worker] sync loop initialized', {
    syncIntervalMs: config.syncIntervalMs,
    nowPlayingIntervalMs: config.nowPlayingIntervalMs,
    enableNowPlaying: config.enableNowPlaying,
  });
}

startWorker();
