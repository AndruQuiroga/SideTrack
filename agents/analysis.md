# agents/analysis.md — Taste, Mood & Recommendation Logic

## Purpose

Define tasks for the **analysis layer** responsible for:

- Turning listening data + audio features into meaningful taste profiles.
- Computing user–user compatibility.
- Powering recommendation and playlist-generation features.

This layer is largely **algorithmic/ML-focused** and sits behind the API, typically invoked via workers.

---

## Context Highlights

- We rely on facts from:
  - Spotify audio features (energy, valence, danceability, tempo, etc.).
  - Genre tags (from MusicBrainz/Spotify or curated tags).
  - Aggregated ListenEvents per user.
- Output:
  - `TasteProfile` objects with:
    - Genre breakdown.
    - Mood/energy vectors.
    - Time-of-day patterns.
  - Compatibility scores between users.
  - Recommendation lists.

We aim for **simple, interpretable methods first**, with clear paths to more advanced ML.

---

## Tasks

### analysis/feature-schema

**Goal:** Define a consistent schema for per-track features.

**Fields (minimum):**

- `energy` (0–1)
- `valence` (0–1, happiness/positivity)
- `danceability` (0–1)
- `tempo` (BPM)
- `acousticness` (0–1)
- `instrumentalness` (0–1)
- Optional: `loudness`, `speechiness`

**Steps:**

1. Create a `TrackFeatures` model/table (if not yet defined).
2. Map Spotify feature fields to this schema.
3. Optionally define an embedding vector representation for ML:
   - For example, a fixed-length float vector combining normalized features.

**Acceptance Criteria:**

- There is a single place where track features are defined and documented.
- Worker jobs can populate and read this schema reliably.

---

### analysis/taste-profile-design

**Goal:** Design the structure of `TasteProfile` and the main aggregation logic.

**Dimensions:**

- **Genre distribution:**
  - Distribution over genres, subgenres or tags.
- **Feature averages:**
  - Average energy, valence, danceability, tempo, etc.
- **Temporal behavior:**
  - Optional distribution over time-of-day or weekday (e.g., morning vs evening moods).

**Steps:**

1. Define the structure:
   - JSON schema or typed class with fields:
     - `genre_histogram: {genre: float}`
     - `feature_means: {energy: float, ...}`
     - `time_of_day_histogram: {bucket: float}` (optional).
2. Document how listens are weighted:
   - Equal weight per listen.
   - Or recency-weighted (e.g. exponential decay).

3. Provide reference functions:
   - `compute_taste_profile(listens, track_features) -> TasteProfile`.

**Acceptance Criteria:**

- `TasteProfile` schema is stable and documented.
- Test data can be run through a function to produce a profile.

---

### analysis/taste-profile-implementation

**Goal:** Implement and test the concrete taste profile computation.

**Steps:**

1. Implement a Python module in `apps/worker` or `apps/api/analysis`:
   - Accepts:
     - List of `ListenEvent`s for a user.
     - Mapping from track IDs to `TrackFeatures` & genre tags.
   - Produces:
     - A `TasteProfile` object.

2. Handle edge cases:
   - Users with very few listens (fallback or mark as incomplete).
   - Tracks lacking features (ignore or handle separately).

3. Write unit tests:
   - Known input sets with expected distributions.

**Acceptance Criteria:**

- Function passes tests and is deterministic.
- Worker can call this function and store results via the API.

---

### analysis/compatibility-metric

**Goal:** Define and implement the compatibility metric between two users.

**Ingredients:**

- Overlap in top artists/albums.
- Cosine similarity between:
  - Genre histogram vectors.
  - Feature means vectors (energy, valence, etc.).

**Steps:**

1. Define a scoring formula:
   - Example:
     - `score = 0.4 * artist_overlap + 0.3 * genre_similarity + 0.3 * feature_similarity`
   - Where each term is normalized 0–1.

2. Implement functions:
   - `compute_artist_overlap_score(profile_a, profile_b)`.
   - `compute_genre_similarity(profile_a, profile_b)`.
   - `compute_feature_similarity(profile_a, profile_b)`.
   - `compute_compatibility(profile_a, profile_b) -> float (0-100)`.

3. Ensure score is:
   - Symmetric.
   - Stable (changes slowly as tastes shift).
   - Interpretably mapped to descriptions (e.g., 80+ is “very compatible”).

**Acceptance Criteria:**

- Compatibility scores can be computed for any pair with taste profiles.
- API endpoint `GET /users/{a}/compatibility/{b}` can call these functions.

---

### analysis/recommendation-strategy-mvp

**Goal:** Implement a first-pass recommendation strategy using taste and social data.

**MVP Concept:**

- “Users like you also enjoyed …”
- “Club favorites you missed.”

**Steps:**

1. **Collaborative-ish approach:**
   - For a given user:
     - Find top N similar users.
     - Collect albums they rated highly or listen to often.
     - Filter out albums the target user already listened to/rated.

2. **Club integration:**
   - Consider high-rated club winners as candidates.
   - Promote winners from genres the user likes which they haven’t rated.

3. Score and rank candidates:
   - Simple scoring based on:
     - How many similar users liked it.
     - Average rating from similar users.
     - Genre match with target user.

4. Package results into a `UserRecommendations` data structure:
   - `album_id`, `score`, `reason` string.

**Acceptance Criteria:**

- For users with enough data, function returns a list of candidate albums with reasons.
- Worker job can compute and store these recommendations periodically.

---

### analysis/playlist-templates

**Goal:** Define templates for auto playlists using the analysis outputs.

**Playlists:**

- **Friend Blend:** combine tracks from you and a friend’s favorite recent listens.
- **Mood Match:** picks tracks matching current mood (e.g., high-energy, happy).
- **Club Catch-up:** selects tracks from past club winners you haven’t listened to yet.

**Steps:**

1. For each playlist type:
   - Define input parameters (user ID, friend ID, mood, etc.).
   - Define selection rules using:
     - Taste profile.
     - Recent listens.
     - Club winners & ratings.

2. Implement selection logic returning:
   - Ordered list of track IDs.

3. Ensure it’s easy for workers to:
   - Turn these track IDs into actual Spotify playlists via API.

**Acceptance Criteria:**

- Playlist builders can be invoked programmatically.
- Given test users with synthetic data, builders return plausible track lists.

---

### analysis/future-ml-hooks (optional)

**Goal:** Prepare code structure for plugging in more advanced ML later without breaking the system.

**Steps:**

1. Abstract key points:
   - Create interfaces for:
     - Taste profile computation.
     - Compatibility scoring.
     - Recommendation generation.

2. Provide default simple implementations.
3. Document where a learned model could be inserted:
   - E.g., `ml/recommender.py` that can be swapped in.

**Acceptance Criteria:**

- The system can evolve toward ML-heavy methods without large refactors.
