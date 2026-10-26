# Environment variables

Every variable the code reads, by service. `.env.example` lists them for local `docker compose`; `deploy/README.md` covers Stache-Rack. Rows marked **secret** must come from a Swarm secret in production, never from stack env.

How secrets are read:
- **API (Python):** env var first, then a file of the same lowercase name in `SIDETRACK_SECRETS_DIR` (default `/run/secrets`), e.g. `/run/secrets/sidetrack_web_api_token`.
- **Web and bot (Node):** env var first, then the file named by `<NAME>_FILE`, e.g. `DISCORD_BOT_TOKEN_FILE=/run/secrets/sidetrack_discord_bot_token`.

## API (`sidetrack.api`, also the Postgres worker and Alembic)

| Variable | Secret | Default | Notes |
| --- | --- | --- | --- |
| `SIDETRACK_ENV` | | `production` | `development` allows missing client tokens (those clients get 401) and generates a link secret |
| `DATABASE_URL` | **secret** | `sqlite:///./sidetrack.db` | `postgresql+psycopg://user:pass@host:5432/db`; also read by Alembic |
| `SIDETRACK_WEB_API_TOKEN` | **secret** | none | The web server's own token; required in production (ADR 0009) |
| `SIDETRACK_BOT_API_TOKEN` | **secret** | none | The bot's own token; required in production and distinct from the web token |
| `SIDETRACK_LINK_SECRET` | **secret** | random in development | Signs account-linking state; API only |
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
| `SIDETRACK_BOT_API_TOKEN` | **secret** | Or `SIDETRACK_BOT_API_TOKEN_FILE`; the bot's own API token |
| `DISCORD_BOT_TOKEN` | **secret** | Or `DISCORD_BOT_TOKEN_FILE` (alias `DISCORD_TOKEN`) |
| `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID` | | Slash-command registration |
| `SIDETRACK_NOMINATIONS_FORUM_ID` | | Forum channel for nominations |
| `SIDETRACK_ADMIN_ROLE_IDS` | | Comma-separated role IDs |
| `DISCORD_MEMBERS_INTENT` | | `true` requests the privileged Server Members intent so members leaving the guild lose club access; enable it in the Discord developer portal first |
| `SIDETRACK_RETRY_ATTEMPTS`, `SIDETRACK_RETRY_DELAY_MS` | | Optional, defaults 3 and 250 |

## Web (`apps/web`)

| Variable | Secret | When read | Notes |
| --- | --- | --- | --- |
| `SIDETRACK_API_BASE_URL` | | Runtime | Internal API URL; only the web server calls the API, browsers never do |
| `SIDETRACK_WEB_API_TOKEN` | **secret** | Runtime | Or `SIDETRACK_WEB_API_TOKEN_FILE`; server-side only |
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
