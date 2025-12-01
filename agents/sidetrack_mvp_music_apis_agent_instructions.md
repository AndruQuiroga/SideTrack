# Sidetrack MVP – Music Metadata & Listen Ingest

**Audience:** Coding agent (e.g., Codex-style) implementing the MVP music stack for Sidetrack.

**Scope:**
- Use **MusicBrainz Web Service (WS/2)** as canonical metadata source (artists, albums, tracks).
- Use **Last.fm** as the **primary listen source** (recent tracks, top artists/albums/tracks).
- Use **ListenBrainz** as a **secondary/open listen source** (optional but supported in MVP).
- Do **not** implement MCP tools here. Just implement standard HTTP-based client code, internal service functions, and DB integration points.

The goal is to give you **clear, deterministic instructions** so you can:

1. Create reusable client modules for MusicBrainz, Last.fm, and ListenBrainz.
2. Implement core Sidetrack operations for **metadata lookup** and **listen ingestion**.
3. Normalize all data around **MusicBrainz IDs (MBIDs)** as much as possible.

---

## 1. General Implementation Rules

### 1.1 Languages & Libraries

- Assume implementation in **Python** for now.
- Use the following libraries where appropriate:
  - `httpx` or `requests` for HTTP.
  - Standard library modules only otherwise (no need for ORM details in this doc).
- Do **not** commit any secrets. Assume API keys and tokens come from environment variables.

### 1.2 Configuration & Environment Variables

Define (or expect) these environment variables:

- `SIDETRACK_MUSICBRAINZ_APP_NAME` – e.g., `"Sidetrack/0.1 (contact@example.com)"`.
- `LASTFM_API_KEY` – Last.fm API key.
- `LASTFM_API_SECRET` – Last.fm API secret (might be needed for future authenticated methods, but MVP can use key-only methods).
- `LISTENBRAINZ_USER_AGENT` – User-agent string when calling ListenBrainz.

The agent should **read** these values; if missing, fail fast with a clear error.

### 1.3 Error Handling & Rate Limiting

- Wrap all external HTTP calls in helper functions that:
  - Set appropriate `User-Agent` header.
  - Handle non-200 responses by raising a structured error (e.g., custom `ExternalApiError`).
  - Optionally apply basic retry (e.g., up to 3 retries for transient 5xx / network errors).
- MusicBrainz enforces a gentle rate limit. For MVP, it is enough to:
  - Avoid bursts (e.g., sleep a small amount between many calls if needed).
  - Be prepared for HTTP 503/429 and back off.

### 1.4 Canonical Entity Keys

Internally, Sidetrack should aim to use the following canonical keys:

- **Artist:** MusicBrainz **Artist MBID**.
- **Album:** MusicBrainz **Release Group MBID** (primary) and optionally a specific **Release MBID**.
- **Track:** MusicBrainz **Recording MBID**.

When an external API doesn’t provide MBIDs, you should:

1. Attempt a MusicBrainz search to resolve to MBIDs.
2. If still not resolvable, create a temporary internal ID and mark the track as **unresolved** (no MBID yet).

---

## 2. MusicBrainz Web Service (WS/2)

### 2.1 Basics

- **Base URL:** `https://musicbrainz.org/ws/2/`
- All requests should:
  - Use `fmt=json` (JSON output).
  - Include `User-Agent` header with `SIDETRACK_MUSICBRAINZ_APP_NAME`.
- There are three general types of requests:
  - **Lookup:** by MBID (e.g. `/ws/2/artist/{mbid}`)
  - **Search:** text search (e.g. `/ws/2/release-group?query=...`)
  - **Browse:** relational navigation (e.g. releases in a release-group).

### 2.2 Shared HTTP Helper

Implement a helper function for all MusicBrainz calls:



You can adapt this to sync code if needed; the pattern is what matters.

### 2.3 MVP Operations

For Sidetrack MVP, we need:

1. **Album identification** from `artist_name + album_title` (club nomination / search).
2. **Album track listing** for the chosen album (to map listens back to album context).
3. **Artist search & lookup**.
4. **Recording (track) search** for mapping Last.fm tracks to MBIDs.

#### 2.3.1 Search Album (Release Group)

**Goal:** Given `artist_name` and `album_title` (and optionally `year`), find the best matching **release group**.

**Endpoint:** `GET /ws/2/release-group`

**Parameters:**
- `query` – Lucene-style search query.
- `limit` – number of results (e.g. 5–10).
- `offset` – pagination (MVP usually doesn’t need).
- `fmt` – `json`.

**Query construction (MVP heuristic):**

- Base query: `artist:"{artist_name}" AND release:"{album_title}"`
- If year is known: append `AND firstreleasedate:{year}` or filter results by `first-release-date` manually.

**Example call:**



**Expected JSON fields (simplified, for MVP):**

- `"release-groups"`: list of objects, each with:
  - `"id"`: release group MBID.
  - `"title"`: album title.
  - `"first-release-date"`: string `YYYY-MM-DD` or `YYYY-MM` or `YYYY`.
  - `"primary-type"`: e.g., `"Album"`, `"EP"`.
  - `"artist-credit"`: list with `"name"` and nested `"artist"` (contains MBID).

**Selection heuristic inside Sidetrack:**

1. Prefer results where `primary-type` is `Album`.
2. Prefer earliest `first-release-date`.
3. Prefer exact (case-insensitive) title match.

Return a small internal structure like:



Use this to present options to the user or choose automatically where confident.

#### 2.3.2 Get Releases + Track Listing for a Release Group

Once a **release-group MBID** is chosen, fetch its releases and select a preferred one.

**Endpoint (browse):** `GET /ws/2/release`

**Parameters (MVP):**
- `release-group={release_group_mbid}`
- `inc=recordings+media`
- `limit=100`
- `fmt=json`

**Example helper:**



**Important fields from JSON (MVP):**

- `"releases"`: list of releases. For each release:
  - `"id"`: release MBID.
  - `"title"`.
  - `"date"`: release date.
  - `"country"`.
  - `"media"`: list of medium objects, each with:
    - `"track-count"`.
    - `"tracks"`: list with:
      - `"id"`: track MBID (track entity).
      - `"recording"` with fields:
        - `"id"`: recording MBID (this is our **Track MBID**).
        - `"title"`.
        - `"length"`: duration in milliseconds.
      - `"position"` (track number).
      - `"number"` (string track number).

**MVP selection strategy for preferred release:**

1. Filter to `country` == user’s default (e.g., `US`) if provided.
2. Prefer releases with non-empty `date`.
3. Among remaining, choose the one with earliest `date`.

The agent should produce a normalized internal track list:



#### 2.3.3 Artist Search & Lookup

**Search endpoint:** `GET /ws/2/artist`

Parameters:
- `query=artist:"{name}"`
- `limit`
- `fmt=json`



Response structure (simplified):
- `"artists"`: list with objects:
  - `"id"`: artist MBID.
  - `"name"`.
  - `"sort-name"`.
  - `"country"` (optional).
  - `"disambiguation"` (optional).

**Lookup endpoint:** `GET /ws/2/artist/{mbid}` (for now, `inc` not required in MVP; you can add `inc=aliases+tags+genres` later if needed).

#### 2.3.4 Recording Search (Track Resolution)

**Endpoint:** `GET /ws/2/recording`

Parameters (MVP heuristic):
- `query=recording:"{track_name}" AND artist:"{artist_name}"`
- `limit=5`
- `fmt=json`

Optional: include album name to narrow down:
- `query=recording:"{track_name}" AND artist:"{artist_name}" AND release:"{album_name}"`



Response (simplified):
- `"recordings"`: list of objects:
  - `"id"`: recording MBID.
  - `"title"`.
  - `"length"` (optional, ms).
  - `"artist-credit"` list (with names and artist MBID).
  - `"releases"` (optional) listing associated releases.

**Matching heuristic for Last.fm / ListenBrainz tracks:**

1. Compare track titles case-insensitively.
2. Compare primary artist name.
3. If duration is available on both sides, pick candidate with smallest duration difference (e.g. < 3 seconds).

Return best candidate or `None` if no confident match.

---

## 3. Last.fm (Primary Listen Source)

### 3.1 Basics

- **Root URL:** `https://ws.audioscrobbler.com/2.0/`
- All methods use `GET` with query parameters.
- Common parameters:
  - `method` – e.g., `user.getRecentTracks`.
  - `api_key` – from `LASTFM_API_KEY`.
  - `format=json` – always request JSON.

### 3.2 Shared HTTP Helper



### 3.3 Methods Required for MVP

1. **Recent tracks** – `user.getRecentTracks` (primary listen ingest).
2. Optionally: **top artists**, **top albums** – `user.getTopArtists`, `user.getTopAlbums` for quick taste summary.

#### 3.3.1 `user.getRecentTracks` – Listen Ingestion

**Purpose:**
- Pull a user’s recent scrobbles as the primary listen source.
- Also includes a `nowplaying` flag for current track.

**Required parameters:**
- `method=user.getRecentTracks`
- `user` – Last.fm username.
- `api_key` – handled by helper.
- `format=json` – handled by helper.

**Optional parameters (MVP):**
- `limit` – number of tracks per page (e.g. 200).
- `page` – pagination.
- `from` – UNIX timestamp (seconds) to only get scrobbles after this time.

**Example helper:**



**Important response fields (MVP):**

Top-level:
- `"recenttracks"` object containing:
  - `"track"`: list of tracks.
  - `"@attr"`: pagination info (page, totalPages, total, user).

Each track item (simplified):

- `"name"` – track title.
- `"artist"` – object with `"#text"` (artist name), possibly `"mbid"`.
- `"album"` – object with `"#text"` (album title), possibly `"mbid"`.
- `"date"` – object with:
  - `"uts"` – UNIX timestamp (string seconds since epoch).
  - `"#text"` – human-readable date.
- `"@attr"` – may contain `"nowplaying": "true"` for currently playing track.
- `"mbid"` – track-level MBID (often empty or unreliable; treat as hint, not absolute truth).

**MVP ingest algorithm for Last.fm:**

Implement a function, for example:



The function `resolve_track_to_mb_recording` (see §2.3.4) should contain the MusicBrainz matching logic.

#### 3.3.2 `user.getTopArtists` / `user.getTopAlbums` (Taste Snapshot)

**Purpose (MVP optional):**
- Quickly compute a user’s long-term taste summary when they connect their Last.fm account.

**Example helper:**



Response essentials:
- `"topartists"` object with:
  - `"artist"` list, each with:
    - `"name"`.
    - `"playcount"`.
    - `"mbid"` (may be present).

Similar for `user.getTopAlbums`.

MVP usage:
- When a user first connects Last.fm, optionally fetch top artists/albums for `overall` and store as precomputed taste features (e.g., for profile summary).

---

## 4. ListenBrainz (Secondary Listen Source)

### 4.1 Basics

- **Root URL:** `https://api.listenbrainz.org/1/`
- Primary endpoints used in MVP:
  - `GET /1/user/{user_name}/listens`
  - `GET /1/user/{user_name}/playing-now`
- No API key is required for public read operations.
- Set a descriptive `User-Agent` header using `LISTENBRAINZ_USER_AGENT` or reuse Sidetrack’s app name.

### 4.2 Shared HTTP Helper



### 4.3 `GET /1/user/{user_name}/listens`

**Purpose:**
- Fetch a user’s listens directly from ListenBrainz.
- Useful for users who already send scrobbles to ListenBrainz or don’t want to use Last.fm.

**Endpoint:**
- `GET /1/user/{user_name}/listens`

**Common query parameters (MVP):**
- `min_ts` – minimum Unix timestamp (seconds) for listens to include.
- `max_ts` – maximum timestamp (optional; we typically leave it empty and page backwards over time by adjusting `min_ts`).
- `count` – maximum number of listens to return (up to around 100 per request in many implementations).

**Example helper:**



**Expected JSON (simplified):**

- Top-level:
  - `"payload"`:
    - `"listens"`: list of listen objects.
    - `"count"`: number of listens returned.

Each listen object (simplified):

- `"listened_at"`: Unix timestamp (integer seconds).
- `"track_metadata"` object with fields:
  - `"artist_name"`.
  - `"track_name"`.
  - `"release_name"` (album title) – optional.
  - `"additional_info"` object which may contain:
    - `"recording_msid"` – internal ListenBrainz recording ID.
    - `"recording_mbid"` – MusicBrainz recording MBID.
    - `"artist_msid"`, `"release_mbid"`, etc.

### 4.4 MVP Ingest Logic for ListenBrainz

Implement a function analogous to the Last.fm ingest, for example:



### 4.5 `GET /1/user/{user_name}/playing-now`

**Purpose:**
- Expose “now playing” info on user profiles or in the Discord bot.

**Endpoint:** `GET /1/user/{user_name}/playing-now`

Usage pattern is the same as `/listens`, but it returns at most **one** listen and may not include `listened_at`. You can map its `track_metadata` to a `NowPlaying` internal structure similar to the ListenBrainz listens above, but you do **not** insert it as a historical listen event.

---

## 5. Track Resolution: `resolve_track_to_mb_recording`

This is a central function used by both Last.fm and ListenBrainz ingest. It converts external track metadata into a **MusicBrainz recording MBID**.

### 5.1 Function Contract



### 5.2 MVP Heuristic

1. If `lastfm_track_mbid` is given and non-empty:
   - Optionally verify by doing a `GET /ws/2/recording/{mbid}` lookup.
   - If lookup succeeds, return this MBID.
2. Else:
   - Perform Recording search as in §2.3.4.
   - Filter candidates by:
     - Case-insensitive equality on `title` vs `track_name`.
     - Case-insensitive equality of at least one artist-credit name vs `artist_name`.
   - If `album_name` provided, prefer recordings associated with releases whose title matches `album_name` (loose case-insensitive equality).
   - If we have durations from the external source and from MB, pick the candidate with minimal duration difference (e.g. < 3 seconds).
3. If multiple equally good candidates remain or no candidate seems credible, return `None` and mark the track as unresolved.

Sidetrack can later run a background job to try resolving unresolved tracks using additional context (e.g., album tracklists once imported).

---

## 6. Internal Integration Points (High-Level)

This section describes where these client functions plug in. You **do not** need to implement the DB/ORM details here; just respect these conceptual responsibilities.

### 6.1 Metadata Layer

Implement a **Metadata Service** module that uses MusicBrainz clients to:

1. Search for albums by `artist + album name`.
2. Persist chosen release-group + release + tracks to Sidetrack DB.
3. Search and resolve tracks and artists as needed.

Expose functions like:



### 6.2 Listen Ingest Layer

Implement a **Listen Ingest Service** module that uses Last.fm and ListenBrainz clients to:

- Incrementally ingest listens for each user.
- Map them to MB recordings.
- Write `ListenEvent` rows referenced by:
  - `user_id` (internal Sidetrack user ID).
  - `recording_mbid` (if resolved).
  - `timestamp` (UTC seconds).
  - `source` (`"lastfm"`, `"listenbrainz"`).
  - `raw_payload` (JSON, for debugging or advanced later analysis).

For each external account you should track:

- `last_ingested_ts` per source.
- Optionally, a `status` / `error` field if ingestion fails.

Scheduling of ingestion (cron, background queue, etc.) is outside this doc; just expose idempotent functions that can be called repeatedly.

---

## 7. What NOT To Implement in MVP

To keep scope manageable, **do not** implement the following in this MVP agent spec:

- Local MusicBrainz mirror or data dumps (use public WS only).
- Spotify integration (can be added later; ignore for now).
- Advanced recommendation or ML-based taste analysis.
- Any MCP tooling adapters.

Focus strictly on:

1. MusicBrainz metadata clients.
2. Last.fm listen and taste ingestion.
3. ListenBrainz listen ingestion (optional, secondary).
4. Track resolution around MBIDs.

Once these are solid, higher-level features (Discord bot integration, web UI, analytics) can rely on clean, normalized data provided by this MVP stack.

