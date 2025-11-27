# Sidetrack Environment Variables

This repo uses a single `.env` at the repo root. Copy `.env.example` to `.env` and fill in the values that apply to your setup. Docker Compose, the API, the bot, the worker, and the web app all read from the same file.

## Core services
- `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT` — database connection pieces used to assemble `DATABASE_URL`.
- `DATABASE_URL` — full SQLAlchemy/Postgres URL. In Compose this points at `db`.
- `REDIS_URL` — Redis connection string (default `redis://redis:6379/0` in Compose).
- `SIDETRACK_API_BASE_URL` — internal API address for bot/worker/web containers (e.g. `http://api:8000`).
- `SIDETRACK_API_TOKEN` — shared bearer token for bot/worker → API calls.

## Discord bot
- `DISCORD_BOT_TOKEN` — bot token from the Discord developer portal.
- `DISCORD_CLIENT_ID` — application/client id.
- `DISCORD_GUILD_ID` — target guild for club automation.

## Web (Next.js) auth & API access
- `NEXT_PUBLIC_API_BASE_URL` — public API base URL for the browser (e.g. `http://localhost:8000`).
- `NEXTAUTH_URL` — site origin passed to NextAuth.
- `NEXTAUTH_SECRET` — secret used by NextAuth session cookies.

## Third-party integrations
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` — Spotify OAuth credentials.
- `LASTFM_API_KEY`, `LASTFM_API_SECRET` — Last.fm API keys.
- `MUSICBRAINZ_RATE_LIMIT` — optional throttle for MusicBrainz traffic.

## Feature flags & misc
- `SPOTIFY_RECS_ENABLED`, `LASTFM_SIMILAR_ENABLED` — booleans that gate recommendation features.
- `AUDIO_ROOT`, `CACHE_DIR` — filesystem paths for audio assets and temporary caches.
- `TZ` — default timezone for containers and scheduler defaults.

> Task refs: core/env-config, core/init-monorepo. Keep this list in sync with `.env.example` and Docker Compose expectations when adding new services or integrations.
