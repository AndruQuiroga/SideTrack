# Worker Jobs

This directory scaffolds the background worker processes responsible for syncing external listening data and running batch computations for stats and recommendations.

## Listening sync + metrics

The worker now includes provider connectors for Spotify, Last.fm, and ListenBrainz. It refreshes tokens, fetches recently played tracks, deduplicates by track + timestamp, and upserts them as `listen_events` via the API. Sync loops run on a configurable interval (`WORKER_SYNC_INTERVAL_MINUTES`), with optional “now playing” sweeps controlled by `WORKER_ENABLE_NOW_PLAYING`/`WORKER_NOW_PLAYING_SECONDS`.

Metrics and last-sync cursors are exposed via a lightweight status server on `WORKER_STATUS_PORT` (defaults to `8700`) so bot/web surfaces can observe success/error counts.
