# agents/api.md — Backend API & Data Model

## Purpose

Define tasks for designing and implementing the **Sidetrack backend API**, including:

- Core data models (users, linked accounts, music entities, club entities, listening events, taste profiles).
- Auth and integration with Discord, Spotify, Last.fm/ListenBrainz.
- Endpoints for the Discord bot (club automation).
- Endpoints for the web (archive browsing, profiles, social features).
- Plumbing for analysis and workers.

Assume a **FastAPI + PostgreSQL** stack unless explicitly changed.

---

## Context Highlights

Key ideas from the high-level design:

- The API is the **single source of truth** for:
  - Weekly club data: weeks, nominations, votes, winners, ratings.
  - Users and their external IDs (Discord ID, Spotify ID, Last.fm username, etc.).
  - Music catalog entries (albums/tracks) referenced by club and listening data.
  - Listening events and derived taste profiles.

- Discord bot:
  - Writes structured club data via the API, never directly to the DB.
  - Needs idempotent operations (e.g. safe to re-send an event).

- Web:
  - Reads mostly via **read-optimized endpoints** for archive & profiles.
  - Writes for user actions: linking accounts, rating albums, following users, etc.

- Workers:
  - Use the API (or direct DB access) to fetch users & tasks (e.g. needs-sync queue), then write back listening data and taste profiles.

---

## Tasks

### api/setup

**Goal:** Scaffold the API application with FastAPI, database connection, and minimal health checks.

**Steps:**

1. Initialize a FastAPI app in `apps/api`:
   - Entrypoint (e.g. `main.py`) with:
     - `/health` endpoint.
     - Version info.

2. Configure SQLAlchemy or an ORM (e.g. SQLModel or Tortoise) to connect to Postgres.
3. Add alembic or migrations tooling:
   - Base migration for an empty schema.

**Acceptance Criteria:**

- API runs locally and responds to `/health`.
- Database connection is tested at startup or via a small diagnostic endpoint.

---

### api/schema-core

**Goal:** Define the core database models and Pydantic schemas for:

- User
- LinkedAccount
- Album
- Track

**Steps:**

1. **User model:**
   - `id` (internal).
   - Display name.
   - Optional username/handle.
   - Created/updated timestamps.

2. **LinkedAccount model:**
   - Foreign key to `User`.
   - Provider type: `discord`, `spotify`, `lastfm`, `listenbrainz`.
   - Provider ID (e.g., Discord snowflake, Spotify user ID).
   - Tokens where relevant (Spotify refresh token, Last.fm session key).
   - Metadata (scopes, etc.).

3. **Album & Track models:**
   - `Album`: title, artist name(s), release year, MusicBrainz/Spotify IDs, cover art URL.
   - `Track`: title, album FK, artist name(s), duration, IDs (MB/Spotify).

4. Pydantic schemas mirroring the above for API responses:
   - Distinguish between internal DB models and external API schemas.

5. Create migrations for these tables.

**Acceptance Criteria:**

- Models exist with fields that cover the needs of the club archive and listening data.
- Can create/read/update basic instances in a dev environment.

---

### api/schema-club

**Goal:** Define models for **weekly club operations**.

**Models:**

- `Week`
- `Nomination`
- `Vote`
- `Rating`
- Possibly `ThreadRef` or a generic `ExternalMessageRef` for Discord linkage.

**Steps:**

1. **Week:**
   - `id`, week number, week label/title (e.g., `WEEK 003 [2025-11-24]`).
   - `date_discussion` (datetime).
   - `winner_album_id` (FK to `Album`), nullable until decided.
   - Optional external IDs (Discord category/thread IDs) for navigation.

2. **Nomination:**
   - FK to `Week`.
   - FK to `User` (nominator).
   - FK to `Album` (nominee).
   - Pitch text.
   - Pitch track URL.
   - Tags (genre, decade, country) – could be a separate tag table or a JSON field.

3. **Vote:**
   - FK to `Week`.
   - FK to `User` (voter).
   - FK to `Nomination`.
   - Rank: `1` or `2`.
   - Computed score (2 or 1) can be stored or computed from rank.
   - Unique constraint: one vote per (week, user, rank).

4. **Rating:**
   - FK to `Week`.
   - FK to `User`.
   - FK to `Album` (should match winner).
   - Numeric rating: 1.0–5.0 (half increments).
   - Favorite track (string, optional).
   - Freeform review text.

5. Add migrations and Pydantic schemas.

**Acceptance Criteria:**

- Models represent a full weekly cycle.
- Unique constraints enforce club rules (e.g., one rating per user per week).
- Ready for Discord bot to consume via API.

---

### api/endpoints-club-weeks

**Goal:** Implement endpoints for basic week lifecycle operations.

**Endpoints (suggested):**

- `GET /club/weeks` — list weeks (filter by date, include winners).
- `GET /club/weeks/{id}` — detail including:
  - Week metadata.
  - Winner album and stats.
  - Nominations + poll stats.
  - Ratings summary.

- `POST /club/weeks` — create a new week (bot/admin only).
- Optionally: `PATCH /club/weeks/{id}` — update (winner, dates, etc.).

**Acceptance Criteria:**

- Web can render:
  - A winners gallery using `/club/weeks`.
  - A detail page using `/club/weeks/{id}`.
- Discord bot can create and update weeks without DB knowledge.

---

### api/endpoints-nominations

**Goal:** Provide endpoints for Discord bot to sync nomination data.

**Endpoints:**

- `POST /club/weeks/{week_id}/nominations` — upsert a nomination.
  - Body: album metadata or IDs, nominator user/Discord ID, pitch, pitch track URL, tags.
- `GET /club/weeks/{week_id}/nominations` — list all nominations for that week.

**Notes:**

- Bot will parse messages and call this endpoint.
- API should:
  - Resolve or create the underlying `Album`.
  - Resolve or create the `User` based on Discord ID (link via `LinkedAccount`).
  - Ensure idempotency (same user + album + week doesn’t create duplicates).

**Acceptance Criteria:**

- Nominations created by bot appear in web week detail view.
- Re-processing messages doesn’t create duplicates.

---

### api/endpoints-votes

**Goal:** Enable ranked voting sync from Discord bot.

**Endpoints:**

- `POST /club/weeks/{week_id}/votes` — set or update a user’s vote.
  - Body: user (Discord ID), nomination ID or album reference, rank (1 or 2).
- `GET /club/weeks/{week_id}/votes/summary` — compute:
  - Per-nomination point totals.
  - Sorted ranking.
  - Tie-breaker logic (most 1st place).

**Acceptance Criteria:**

- Bot can send a single call per user per rank.
- Summary matches poll results displayed in Discord.
- Week detail view can show poll results with correct scores and ties resolved.

---

### api/endpoints-ratings

**Goal:** Store and expose ratings collected in Discord and on the web.

**Endpoints:**

- `POST /club/weeks/{week_id}/ratings` — create/update a rating.
  - Body: user (Discord ID or authed user), rating value, favorite track, review text.
- `GET /club/weeks/{week_id}/ratings` — list ratings (optionally anonymized or truncated for public).
- `GET /club/weeks/{week_id}/ratings/summary` — compute:
  - Average rating.
  - Count of ratings.
  - Distribution (histogram).

**Acceptance Criteria:**

- Bot can post each rating as it parses mini-forms.
- Web can:
  - Show per-week average rating.
  - Show per-rating entries and an optional histogram.

---

### api/music-catalog

**Goal:** Provide a unified API for searching and resolving albums/tracks.

**Responsibilities:**

- Search by album/artist names.
- Resolve canonical IDs (MusicBrainz, Spotify).
- Store normalized metadata for reuse.

**Endpoints:**

- `GET /music/search` — query string, return albums/tracks.
- `POST /music/albums` — create/ensure album exists by external IDs.
- Possibly internal endpoints for workers to refresh metadata.

**Implementation Notes:**

- Perform lookups via:
  - MusicBrainz (remote or local mirror).
  - Spotify search when necessary (for cover art or audio features).
- Cache results in DB to minimize external calls.

**Acceptance Criteria:**

- Given an album from a nomination, API can:
  - Find or create it in the internal catalog.
  - Provide enough data for frontend (title, artist, year, cover URL).

---

### api/integrations-auth

**Goal:** Implement OAuth / auth integration for Spotify and Last.fm/ListenBrainz, plus login for web users.

**Components:**

1. **Web user auth:**
   - Basic session or JWT auth for the site itself.
   - Optionally support “Sign in with Discord” and/or “Sign in with Spotify”.

2. **Link external accounts:**
   - `POST /auth/spotify/link` — start OAuth flow, handle callback.
   - `POST /auth/lastfm/link` — use Last.fm auth dance.
   - Store tokens in `LinkedAccount`.

3. **Token refresh:**
   - Provide utilities for workers to:
     - Refresh Spotify access tokens from stored refresh tokens.
     - Use Last.fm session keys.

**Acceptance Criteria:**

- Users can:
  - Log into the web app.
  - Connect Spotify and Last.fm accounts.
- LinkedAccount records are created and usable by workers.

---

### api/listening-data

**Goal:** Provide endpoints for workers to push listening events and for web to read them.

**Models:**

- `ListenEvent`:
  - FK to `User`.
  - FK to `Track`.
  - Timestamp.
  - Source (`spotify`, `lastfm`, etc.).
  - Duration or play count info if available.

**Endpoints:**

- Internal/worker:
  - `POST /listens/bulk` — ingest batches of listens.
- Public:
  - `GET /users/{user_id}/listens/recent` — recent listening history.
  - `GET /users/{user_id}/summary` — aggregated stats (top artists/albums/genres over periods).

**Acceptance Criteria:**

- Worker can ingest data without direct DB access.
- Web can show basic listening history and stats for profiles.

---

### api/taste-profiles

**Goal:** Persist taste analysis outputs and expose them to the frontend.

**Model:**

- `TasteProfile`:
  - FK to `User`.
  - JSON or structured columns for:
    - Genre distribution.
    - Mood/energy axes.
    - Time‑of‑day patterns.
  - Last computed timestamp.

**Endpoints:**

- `GET /users/{user_id}/taste` — return taste profile.
- Optionally:
  - `POST /users/{user_id}/taste` — worker‑only endpoint to upsert from analysis jobs.

**Acceptance Criteria:**

- Worker can update taste profiles.
- Web can visualize taste data via a single call.

---

### api/compatibility

**Goal:** Provide a compatibility score and explanation between two users.

**Inputs:**

- Two user IDs.
- Their taste profiles and overlapping artists/albums.

**Endpoint:**

- `GET /users/{user_a_id}/compatibility/{user_b_id}`:
  - Returns a numeric score (0–100).
  - Lists shared top artists and albums.
  - Optional explanation strings (e.g., “You both love melodic hip-hop and 2010s alt rock”).

**Implementation Notes:**

- Start with a simple heuristic:
  - Jaccard similarity over top N artists + a distance between taste vectors.
- Future: plug in ML or more complex metrics.

**Acceptance Criteria:**

- Endpoint returns stable, deterministic output for given profiles.
- Web can render compatibility cards with this output.

---

### api/admin-and-moderation

**Goal:** Provide minimal admin controls for:

- Fixing data issues (wrong tags, typos).
- Hiding/removing inappropriate reviews.
- Overriding week winners if something goes wrong.

**Endpoints:**

- `POST /admin/weeks/{id}/override-winner`
- `DELETE /admin/reviews/{id}`
- etc., protected by admin auth.

**Acceptance Criteria:**

- Admin‑protected routes exist.
- Basic moderation actions are possible for maintainers.
