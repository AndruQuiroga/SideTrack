# Environment variables

Every variable the code reads, by service. `.env.example` lists them for local `docker compose`; `deploy/README.md` covers Stache-Rack. Rows marked **secret** must come from a Swarm secret in production, never from stack env.

How secrets are read:
- **API (Python):** env var first, then a file of the same lowercase name in `SIDETRACK_SECRETS_DIR` (default `/run/secrets`), e.g. `/run/secrets/sidetrack_api_token`.
- **Web and bot (Node):** env var first, then the file named by `<NAME>_FILE`, e.g. `DISCORD_BOT_TOKEN_FILE=/run/secrets/sidetrack_discord_bot_token`.

## API (`sidetrack.api`, also the Postgres worker and Alembic)

| Variable | Secret | Default | Notes |
| --- | --- | --- | --- |
| `SIDETRACK_ENV` | | `production` | `development` allows a missing API token and generates a link secret |
| `DATABASE_URL` | **secret** | `sqlite:///./sidetrack.db` | `postgresql+psycopg://user:pass@host:5432/db`; also read by Alembic |
| `SIDETRACK_API_TOKEN` | **secret** | none | Required in production; shared with bot and web server |
| `SIDETRACK_LINK_SECRET` | **secret** | random in development | Signs account-linking state; API only |
| `CORS_ORIGINS` | | `["http://localhost:3000","http://localhost:3001"]` | JSON list of browser origins |
| `LASTFM_API_KEY` | | none | |
| `LASTFM_API_SECRET` | **secret** | none | |
| `SPOTIFY_CLIENT_ID` | | none | Metadata only (ADR 0003) |
| `SPOTIFY_CLIENT_SECRET` | **secret** | none | |
| `SIDETRACK_MUSICBRAINZ_APP_NAME` | | `Sidetrack API/0.1` | User-Agent for MusicBrainz; include contact info |
| `SIDETRACK_SECRETS_DIR` | | `/run/secrets` | Where secret files are read from |

## Bot (`apps/bot`)

| Variable | Secret | Notes |
| --- | --- | --- |
| `SIDETRACK_API_BASE_URL` | | Internal API URL, e.g. `http://api:8000` (alias `API_BASE_URL`) |
| `SIDETRACK_API_TOKEN` | **secret** | Or `SIDETRACK_API_TOKEN_FILE` |
| `DISCORD_BOT_TOKEN` | **secret** | Or `DISCORD_BOT_TOKEN_FILE` (alias `DISCORD_TOKEN`) |
| `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID` | | Slash-command registration |
| `SIDETRACK_NOMINATIONS_FORUM_ID` | | Forum channel for nominations |
| `SIDETRACK_ADMIN_ROLE_IDS` | | Comma-separated role IDs |
| `SIDETRACK_RETRY_ATTEMPTS`, `SIDETRACK_RETRY_DELAY_MS` | | Optional, defaults 3 and 250 |

## Web (`apps/web`)

| Variable | Secret | When read | Notes |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | | **Build time** (Docker build arg) | Public API origin for the browser, e.g. `https://api.sidetrack.network` |
| `SIDETRACK_API_BASE_URL` | | Runtime | Internal API URL for server-side calls |
| `SIDETRACK_API_TOKEN` | **secret** | Runtime | Or `SIDETRACK_API_TOKEN_FILE`; server-side only |
| `NEXTAUTH_URL` | | Runtime | Public site origin, e.g. `https://sidetrack.network` |
| `NEXTAUTH_SECRET` | **secret** | Runtime | Or `NEXTAUTH_SECRET_FILE` |
| `DISCORD_CLIENT_ID` | | Runtime | Discord sign-in |
| `DISCORD_CLIENT_SECRET` | **secret** | Runtime | Or `DISCORD_CLIENT_SECRET_FILE` |
| `NEXT_PUBLIC_DISCORD_GUILD_ID` | | Build time | Optional (alias `SIDETRACK_DISCORD_GUILD_ID` at runtime) |

## Postgres container

| Variable | Secret | Notes |
| --- | --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | | |
| `POSTGRES_PASSWORD` | **secret** | On the rack, `POSTGRES_PASSWORD_FILE=/run/secrets/sidetrack_postgres_password` |
