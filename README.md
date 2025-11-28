# Sidetrack

> A Discord-powered album club, public archive, and social music tracking platform.

Sidetrack is a unified project that combines:

1. **Sidetrack Club** — a weekly album club run entirely through Discord.
2. **Public Web Archive** — a sleek site that showcases every week’s winner, nominees, poll results, and ratings.
3. **Social Music Tracker** — a Last.fm/Spotify-powered platform for tracking listening habits, analyzing mood/taste/genre, and comparing your taste with friends.

This repo is being rebooted: the goal is to replace the old Sidetrack code with a cleaner, modular architecture that plays nicely with Codex-based agents.

---

## High-Level Overview

### What Sidetrack Does

* **On Discord (Sidetrack Club)**

  * Runs a weekly cycle:

    * Nominations → Ranked poll (1st/2nd choice) → Winner → Discussion → Ratings.
  * Provides pinned mini-forms for:

    * Nominations (album, pitch, tags).
    * Ratings (1.0–5.0 with half-stars, fav track, final thoughts).
  * Automates:

    * Thread creation for each phase.
    * Reminders for deadlines and discussion time.
    * Tallying votes & announcing the winner.
    * Collecting ratings and posting summaries.

* **On the Web**

  * Public **winners gallery** of all weeks.
  * Detailed **week pages**:

    * Winner album.
    * Full list of nominees & nominator pitches.
    * Poll results (points, rankings).
    * Ratings, reviews, and average score.
  * **User profiles** (for logged-in users):

    * Listening stats (top artists/albums/genres).
    * Mood/taste graphs (energy, valence, etc.).
    * Ratings & reviews history.
  * **Social features**:

    * Follow/friends.
    * “Taste match” / compatibility scores.
    * Activity feed.
    * Friend-blend & mood-based suggestions.

* **Under the Hood**

  * Integrates with:

    * **Spotify** (OAuth, recently played, audio features, playlists).
    * **Last.fm / ListenBrainz** (scrobbles).
    * **MusicBrainz** (metadata / search, potentially via a local mirror).
  * Computes:

    * Per-user **TasteProfile** (genre distribution, mood vectors, etc.).
    * **Compatibility** between users.
    * **Recommendations** (albums you might like, club picks you missed).

---

## Architecture

Sidetrack is organized as a small monorepo with multiple apps and shared packages:

```text
apps/
  bot/       # Discord bot (Sidetrack Club automation)
  api/       # Backend API (FastAPI or similar, Postgres)
  web/       # Web frontend (Next.js + Tailwind)
  worker/    # Background jobs (sync & analysis)

packages/
  shared/    # Shared types, API client(s), common utilities

agents/
  core.md            # Infra/monorepo/env tasks
  api.md             # Backend/API tasks
  bot.md             # Discord bot tasks
  web.md             # Frontend tasks
  worker.md          # Worker/sync tasks
  analysis.md        # Taste/ML tasks
  data-model.md      # Canonical data model & schema

docs/
  reboot.md          # Full reboot plan / narrative
  forms.md           # Web forms helper notes
  api-endpoints.md   # Early API sketch
  ui.md              # UI/UX notes
  legacy-mapping.md  # Legacy-to-new mapping notes

AGENTS.md            # High-level project + agent overview
```

### Conceptual Data Model

Core entities (see `agents/data-model.md` for details):

* `User` + `LinkedAccount` (Discord / Spotify / Last.fm / ListenBrainz).
* `Album` + `Track` (canonical music catalog entries).
* `Week` (one club session), `Nomination`, `Vote`, `Rating`.
* `ListenEvent` (scrobble-like events), `TrackFeatures`, `TasteProfile`.
* Social: `Follow`, `Compatibility`, `UserRecommendation`.

The backend (`apps/api`) is the single source of truth for all of this; the bot, web frontend, and workers all talk to it.

---

## Tech Stack (Target)

> The repo is currently being refactored toward this stack. Some pieces may still be in flux.

* **Backend API**: Python, FastAPI, SQLAlchemy, Postgres, Alembic.
* **Discord bot**: TypeScript (`discord.js`) or Python (`discord.py`), using a small API client.
* **Web**: Next.js (App Router), React, TailwindCSS, React-chart library for visuals.
* **Workers**: Python, same stack as API, using Redis-backed queue (RQ/Celery).
* **Infra**: Docker, docker-compose, Postgres, Redis.

---

## Repo Status & Reboot Plan

This repo previously hosted the original Sidetrack music taste/mood tracker. The **current work is a reboot** that:

1. Introduces a clean, well-normalized domain model (see `agents/data-model.md`).
2. Splits the system into clear services (bot, api, web, worker).
3. Uses a set of **agent task specs** (`AGENTS.md` + `agents/*.md`) to guide Codex in refactoring and building new functionality.

For a full narrative of the reboot scope and goals, see `docs/reboot.md`.

There will be a period where:

* Old code and tables coexist with new ones.
* Data is gradually migrated.
* The README may be “ahead” of the implementation in some places.

See the **Migration Tasks** in `agents/data-model.md`:

* `data-model/audit-existing-schema`
* `data-model/introduce-new-tables-phase1`
* `data-model/migrate-data-phase2`
* `data-model/deprecate-legacy`
* `data-model/indexing-and-performance-pass`

---

## Getting Started (Development)

> These steps are the target workflow; some commands may need adjustment depending on how far along the refactor is.

### Prerequisites

* Node.js (LTS) with `pnpm` (preferred; via corepack).
* Python 3.11 + `uv` for dependency/env management.
* Docker + docker-compose.
* A Discord bot token and test server.
* Spotify dev app credentials, Last.fm credentials (for full integration).

See `docs/package-management.md` for the expected workflows.

### 1. Clone & Install

```bash
git clone <this-repo-url> sidetrack
cd sidetrack

# Install JS/TS deps
pnpm install

# Install Python deps (API + tests)
uv sync --python 3.11 --extra api --extra dev

## Linting & formatting
- Python lint: `uv run --frozen --extra api --extra dev ruff check apps/api apps/worker`
- Python format: `uv run --frozen --extra api --extra dev ruff format apps/api apps/worker`
- Python types: `uv run --frozen --extra api --extra dev mypy apps/api apps/worker`
- JS/TS lint: `pnpm lint`
- JS/TS format: `pnpm format`
```

This repo uses a `pnpm` workspace (`pnpm-workspace.yaml`) that wires together `apps/web`, `apps/bot`, `packages/shared`, and future TypeScript packages.

### 2. Environment Variables

Copy the example env and fill in values:

```bash
cp .env.example .env
```

Key variables (see `agents/core.md` and `config/ENVIRONMENT.md` if present):

* `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_CLIENT_ID` (for Discord bot connection)
* `SIDETRACK_API_TOKEN` (shared secret for bot/worker → API requests)
* `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (default to the Sidetrack schema; see `.env.example`)
* `DATABASE_URL` (Postgres override using `postgresql+psycopg://` syntax)
* `NEXT_PUBLIC_API_BASE_URL` / `SIDETRACK_API_BASE_URL` (web + bot + worker API host)
* `LASTFM_API_KEY`, `LASTFM_API_SECRET`

### 3. Run Services with Docker Compose (Recommended)

```bash
docker compose up --build
```

Expected (target) services:

* `db` – Postgres
* `redis` – Redis
* `api` – FastAPI backend at `http://localhost:8000`
* `web` – TypeScript web bundle served at `http://localhost:3000`
* `bot` – Discord bot (connects to your server)
* `worker` – background jobs

Compose sets `DATABASE_URL` for the API container to point at Postgres and wires
`NEXT_PUBLIC_API_BASE_URL` / `SIDETRACK_API_BASE_URL` to the in-network API
address (`http://api:8000`) for the web, bot, and worker containers. The `.env`
file mirrors these defaults so local and Compose runs use the same values.

If you prefer manual runs in local environment:

```bash
# In one terminal (API)
cd apps/api
uvicorn apps.api.main:create_app --factory --reload

# In another (web)
pnpm --filter @sidetrack/web run build
node apps/web/dist/index.js

# In another (bot)
pnpm --filter @sidetrack/bot run build
SIDETRACK_API_BASE_URL=http://localhost:8000 node apps/bot/dist/index.js

# In another (worker)
pnpm --filter @sidetrack/worker run build
SIDETRACK_API_BASE_URL=http://localhost:8000 node apps/worker/dist/index.js
```

---

## Using Agents (Codex) With This Repo

Sidetrack is designed to be agent-friendly.

### 1. High-Level Context

Start by feeding **`AGENTS.md`** to an agent. It explains:

* What Sidetrack is.
* The main components.
* Core user flows.
* Tech assumptions.

### 2. Component-Specific Work

Then give the agent the relevant `agents/*.md` file, for example:

* **Backend/API work**: `agents/api.md` + `agents/data-model.md`
* **Discord bot work**: `agents/bot.md`
* **Web UI work**: `agents/web.md`
* **Worker/sync work**: `agents/worker.md`
* **Taste/ML logic**: `agents/analysis.md`
* **Infra/monorepo**: `agents/core.md`

Each task has a clear **ID**, goal, steps, and acceptance criteria (e.g. `api/schema-club`, `bot/nominations-parser`, `web/archive/week-detail`).

### 3. Refactor & Cleanup

To clean up existing code and align with the new model:

1. Run tasks from `agents/data-model.md`:

   * `data-model/audit-existing-schema`
   * `data-model/introduce-new-tables-phase1`
2. Then adjust API endpoints per `agents/api.md`.
3. Finally, migrate any old frontend/bot logic toward the new contracts.

---

## Project Roadmap (High-Level)

1. **Core & API**

   * Monorepo setup, env config, Docker compose.
   * Data model & migrations.
   * Basic users + music catalog endpoints.

2. **Discord Bot**

   * Minimal bot: respond to `/ping` and log in.
   * Week lifecycle: create week in API + nomination thread.
   * Nominations parsing + sync.
   * Polls, winner announcement, ratings parsing.

3. **Web Archive**

   * Winners gallery.
   * Week detail pages (read-only from API).
   * Basic club stats.

4. **Tracking & Social**

   * Auth & account linking (Spotify/Last.fm/Discord).
   * Listening sync workers.
   * TasteProfile & compatibility endpoints.
   * Profiles, feed, and taste visualizations.

5. **Recommendations & Playlists**

   * Basic recommendation engine.
   * Friend-blend & mood playlists exported to Spotify.

---

## Contributing

This repo is in an active refactor/reboot phase. If you’re contributing:

* Keep `agents/*.md` up-to-date with any new endpoints, models, or flows.
* Try to keep changes scoped to a small number of tasks at a time.
* When adding new models or endpoints:

  * Update `agents/data-model.md` if you change the domain.
  * Update `agents/api.md` if you add/modify routes.

PRs that bring the codebase closer to the architecture described here (and in `AGENTS.md`) are very welcome.

---

## License

TBD – choose a license once the reboot stabilizes (e.g. MIT/AGPL/etc.).
For now, assume private/internal use while the project is under heavy development.
