# agents/worker.md — Background Jobs (Sync & Analysis)

## Purpose

Define tasks for background workers that:

- Sync listening data from Spotify/Last.fm/ListenBrainz.
- Trigger and run taste analysis jobs.
- Maintain derived stats and clean up old data.

Workers should keep the API responsive by handling long-running and periodic tasks.

Assume Python workers using the same stack as the API (FastAPI + SQLAlchemy) with a queue system (e.g. RQ, Celery) backed by Redis.

---

## Context Highlights

From the design:

- Listening data comes from external services and should be pulled periodically.
- Analysis (taste profiling, recommendations) is computationally heavier and should **not** run in the main request/response path.
- Workers should use the same data models or an internal client to talk to the API/DB.

---

## Tasks

### worker/setup

**Goal:** Scaffold the worker service with job queue integration.

**Steps:**

1. Initialize `apps/worker`:
   - Worker entrypoint (`worker/main.py` or similar).
   - Configure connection to Redis or other queue backend.
2. Define a basic test job (e.g., log a message).
3. Provide `docker-compose` service for worker.

**Acceptance Criteria:**

- Worker can be started and pick up a test job successfully.

---

### worker/user-sync-registry

**Goal:** Maintain a registry of users who need regular listening-data syncs.

**Responsibilities:**

- Track which users have linked Spotify/Last.fm/ListenBrainz accounts.
- Track last successful sync timestamps.
- Provide a way to mark a user as “needs sync”.

**Implementation Outline:**

1. Either:
   - Use DB tables for sync records.
   - Or rely on API endpoints for “list users with linked accounts”.

2. Worker periodically:
   - Fetches list of eligible users.
   - Schedules per-user sync jobs.

**Acceptance Criteria:**

- There is a deterministic way to know which users to sync and how often.
- No user is spammed with too many API calls.

---

### worker/sync-spotify

**Goal:** Fetch recently played tracks from Spotify for linked users and store them as `ListenEvent`s.

**Steps:**

1. For a given user:
   - Use LinkedAccount to retrieve Spotify tokens.
   - Refresh access token if necessary.
   - Call Spotify “recently played” API with `after` parameter set to last sync time.

2. For each track:
   - Resolve/insert `Track` and `Album` via API/music catalog.
   - Create `ListenEvent` with timestamp and source `spotify`.

3. Update last sync time.

**Acceptance Criteria:**

- For a linked Spotify user, new listens appear in DB after worker runs.
- Duplicate events are not created when sync runs multiple times.

---

### worker/sync-lastfm-listenbrainz

**Goal:** Fetch scrobbles from Last.fm and/or listens from ListenBrainz.

**Steps:**

1. Similar to Spotify:
   - Use provider-specific tokens/identifiers from LinkedAccount.
   - Fetch new scrobbles since last sync.
2. Map entries to `Track` and `Album` in our catalog.
3. Insert `ListenEvent`s with correct timestamps and source `lastfm` or `listenbrainz`.

**Acceptance Criteria:**

- Linked Last.fm/ListenBrainz users have listen events populated.
- Data does not conflict with Spotify; duplicates are handled gracefully.

---

### worker/track-feature-population

**Goal:** Ensure tracks in the DB have audio features required for taste analysis.

**Features:**

- Energy, valence, tempo, danceability, etc. from Spotify.
- Optionally custom features computed via DSP/ML.

**Steps:**

1. Identify tracks lacking features:
   - Query DB or use a “needs-analysis” flag.
2. For each track:
   - Fetch Spotify audio features (if Spotify ID available).
   - Store them in a `TrackFeatures` table or JSON field.
3. Optional: queue additional jobs for custom features (e.g. local audio analysis) when feasible.

**Acceptance Criteria:**

- Majority of tracks with listen events have basic audio feature data.
- Taste analysis can rely on these features.

---

### worker/taste-profile-computation

**Goal:** Periodically compute or update each user’s `TasteProfile`.

**Inputs:**

- Recent `ListenEvent`s.
- `TrackFeatures` and `Album` genre tags.

**Steps:**

1. For each active user:
   - Aggregate listens over a defined window (e.g. last 3 months, all-time).
   - Compute:
     - Genre distribution (normalized).
     - Averages over numeric features (energy, valence, tempo).
     - Time-of-day patterns (optional).

2. Serialize result into `TasteProfile` and store via API or direct DB update.

3. Mark `TasteProfile` with `last_computed_at`.

**Acceptance Criteria:**

- Each user with enough listening data has a populated `TasteProfile`.
- Re-running computation periodically updates profiles without duplicating or inflating numbers.

---

### worker/compatibility-precomputation (optional)

**Goal:** Pre-compute compatibility for friend pairs or popular users to make UI snappy.

**Steps:**

1. For each user:
   - Get their friends/followers list.
2. For each pair:
   - Fetch taste profiles.
   - Compute similarity score.
   - Store/refresh in a `Compatibility` table.

**Acceptance Criteria:**

- Compatibility lookups for common pairs are O(1) via DB.
- Web compatibility endpoint is fast for friend pairs.

---

### worker/recommendation-jobs (MVP)

**Goal:** Generate simple recommendation sets that can be served from the API.

**MVP Strategy:**

- Recommend:
  - Albums liked by similar users but not listened to by the target user.
  - OR high-rated club albums the user hasn’t listened to yet.

**Steps:**

1. For each user:
   - Find similar users (by compatibility) above a threshold.
   - Collect albums they rated highly or listen to often.
   - Subtract albums the target user has already listened to or rated.
2. Store a small set (e.g. top 20) recommendations in a `UserRecommendations` table.

**Acceptance Criteria:**

- Users with sufficient data have a list of candidate recommendation entries.
- API can expose them via a simple endpoint.

---

### worker/cleanup-and-maintenance

**Goal:** Prevent unbounded growth and keep the system healthy.

**Tasks:**

- Delete or archive very old raw logs or transient data (where safe/legal).
- Prune old sync jobs, dead rows in job queues, etc.
- Optional: compress or roll up very old ListenEvents into aggregates.

**Acceptance Criteria:**

- DB doesn’t grow uncontrollably from ephemeral or intermediate data.
- Scheduled maintenance jobs run without manual intervention.
