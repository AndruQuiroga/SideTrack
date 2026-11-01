# Proposal

## Why

Mockup 14 of docs/research/MOCKUPS.md sketches a "bridge": the listener picks two tracks
from their own library and gets an ordered list of their own tracks that moves from one
sound toward the other, with a control between "stay close" and "explore". The embeddings
needed for this already exist (862 MuQ-MuLan assets), and neighbour search exists
(`sidetrack/analysis/embeddings/neighbours.py`), but nothing turns them into a sequence.
The research notes (docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md section 2, "Neighbours,
recommendations and why") warn that a path that is smooth in embedding distance does not
guarantee good transitions (tempo, key, energy, lyrics are not modelled), that plain
nearest neighbours collapse into near-duplicates without diversity control (MMR), and
that any such feature must be compared with plain neighbours and a random control before
it makes claims.

## What Changes

- **Bridge request**: the user picks a start and an end track from their own eligible
  library, a length (3 to 12 tracks between the endpoints) and a closeness/exploration
  setting. The API returns an ordered, metadata-only list of tracks from the same library.
- **Method**: waypoints interpolated between the two endpoint vectors in the original
  512-d space; candidates by cosine to each waypoint; greedy selection with maximal
  marginal relevance (MMR) where the setting is the relevance/diversity tradeoff; no
  repeats; endpoints' own tracks excluded; deterministic for the same inputs and versions.
- **Explanation**: each step shows its cosine to the previous step and to the end track as
  plain ranks or labelled similarities, never as a probability or a quality score, and
  states that the method knows nothing about tempo, key, lyrics or mixability.
- **Editing and saving**: the user can remove or replace a step (next candidate),
  reorder, and save the list privately; saved bridges are listable, deletable, and
  removed with the account.
- **Distinct states**: `missing_endpoint`, `endpoint_not_embedded`,
  `endpoint_ambiguous`, `insufficient_candidates` (with counts), `not_evaluated`.
- **Evaluation gate**: blind owner comparison of bridges against plain
  nearest-neighbour lists and a random control from the same library, plus adjacent
  similarity and diversity metrics, before the feature is described as anything more
  than an experiment.

Out of scope:
- Audio playback, audio previews, audio URLs or file paths in responses (ADR 0007).
- Beatmatching, tempo or key matching, crossfades or any claim of DJ-quality transitions.
- Exporting to Spotify or another service as a playlist (Spotify is metadata-only here).
- Tracks outside the user's library, other members' libraries, or club bridges.
- Mood (valence/arousal) or theme endpoints; recorded as an open question.
- New embedding models, window-level vectors or GPU work.

## Capabilities

### New Capabilities
- `analysis/sound-bridge`: building, explaining, editing, saving and deleting an ordered
  metadata-only sequence of the user's own tracks between two endpoints, with explicit
  insufficient states and an evaluation gate. Includes the owner-only web page.

### Modified Capabilities
None.

## Impact

Current state:
- **Observed:** `similar_assets` ranks exact cosine within one model, revision and
  pipeline, excludes the query's own track, returns `embedded=False` when the asset has
  no current embedding, and is not scoped to a user
  (`sidetrack/analysis/embeddings/neighbours.py`).
- **Observed:** embeddings are one mean-pooled, L2-normalised vector per asset from
  non-overlapping 10 s windows over at most the first 180 s; window vectors are not
  stored (`sidetrack/analysis/embeddings/audio.py`).
- **Observed:** no HTTP route uses embeddings; existing analysis routes are
  compatibility, recommendations, taste profiles and tracks
  (`sidetrack/analysis/routes/`, `docs/status.yaml` "Audio embeddings").
- **Observed:** `AudioAsset.track_id` is nullable and `kind` is `full` or `preview`
  (`sidetrack/analysis/models.py`).
- **Assumed:** `resolve-listens-to-audio` provides `audio_for_track` with statuses
  `ok | no_audio | ambiguous | no_embedding`; only `ok` tracks are eligible.
- **Assumed:** per-user libraries are at most a few thousand embedded tracks, so exact
  in-database cosine for each waypoint fits in an API request (measured in task 3.3).

Dependencies:
- `resolve-listens-to-audio` (`analysis/listen-audio-resolution`) for the eligible library.
- `import-listenbrainz-history` (`listening/listenbrainz-import`) for which tracks a user
  listened to.

Affected:
- `sidetrack/analysis/` (bridge module, tables, owner-only routes), `migrations/`,
  `apps/web` (`/listening/bridge`), `packages/api-client`.
- Docs: `docs/MODULES.md`, `docs/AUDIO.md`, `docs/AUDIO-BENCHMARK.md`, `docs/status.yaml`.
