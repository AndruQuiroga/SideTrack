## Context

Mockup 14 (docs/research/MOCKUPS.md) sketches a bridge between two of the user's tracks.
Everything needed is already in Postgres: per-asset 512-d MuQ-MuLan vectors in pgvector
and listen-to-audio links (draft `resolve-listens-to-audio`). No GPU work is required.

Cautions from docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md:
- Section 1: one pooled vector per asset over the first 180 s; no window vectors, so the
  bridge cannot reason about intros, outros or transitions.
- Section 2 "Neighbours, recommendations and why": nearest neighbours collapse into
  near-duplicates; MMR (Carbonell and Goldstein, 1998) trades relevance for diversity;
  smoothness in embedding distance is not transition quality; compare with plain
  neighbours and random controls.
- Section 3: blind owner judgments, recorded runs, abstain or label as experimental.
- Hard rules: never serve audio over HTTP; Spotify metadata-only.

## Goals / Non-Goals

**Goals:**
- A deterministic, explainable, metadata-only sequence from the user's own library.
- A single closeness/exploration control with a measurable effect.
- An evaluation gate against plain neighbours and a random control.

**Non-Goals:**
- Transition quality, tempo or key matching, playback, external playlist export,
  mood or theme endpoints, cross-user bridges.

## Decisions

### 1. Waypoint interpolation with greedy MMR
Waypoints are spherical linear interpolations (slerp) between the L2-normalised endpoint
vectors at n evenly spaced fractions. For each waypoint in order the system picks the
unused eligible track maximising `lambda * cos(c, w) - (1 - lambda) * max cos(c, s)` over
already selected steps (including the start). Five settings map lambda to 0.9, 0.8, 0.7,
0.6 and 0.5.
- Alternative: shortest path on a k-NN graph. Rejected for v1: sensitive to k, can leave
  the endpoint direction and needs a graph build per library.
- Alternative: plain nearest neighbour per waypoint. Kept as the evaluation baseline; it
  tends to repeat near-duplicates and has no exploration control.
- Alternative: linear interpolation. Rejected: midpoints of unit vectors shrink in norm;
  slerp stays on the sphere (cosine ranking is the same up to scale, but slerp keeps
  waypoint spacing even).

### 2. Synchronous computation in the API
Candidate scoring is exact pgvector cosine over the user's eligible assets for each
waypoint (n <= 12), computed in the request. With a few thousand vectors this is small;
no GPU, no queue and no new service.
- Alternative: a queued CPU job with polling. Kept as the fallback if task 3.3 measures
  p95 latency above 2 s on the production library.
- Alternative: load all user vectors into Python and compute with NumPy. Acceptable
  implementation detail if faster; behaviour is identical.

### 3. One row per track
Each track is represented by its preferred asset from `audio_for_track` (`ok` only);
previews are allowed only when no full asset exists, as that function already decides.
Ambiguous links are excluded and endpoints with ambiguous links are rejected, so an
uncertain identity link cannot shape the path. Sonic similarity never creates a link.

### 4. Saved bridges
Table `sound_bridges(id, user_id FK users ON DELETE CASCADE, start_track_id,
end_track_id, setting, method_version, model, revision, steps jsonb (ordered track ids),
created_at, updated_at)`. Saved lists record the method version; a later method version
does not rewrite them.
- Alternative: store only parameters and recompute. Rejected: user edits would be lost
  and libraries change.

### 5. Evaluation and gate
The audio-lab runs, for at least 15 endpoint pairs chosen by the owner, three lists of the
same length: bridge (middle setting), plain nearest neighbour per waypoint, and a random
draw from the eligible library. The owner judges them blind (order shuffled, method
hidden) on "moves from A toward B" and "would listen in this order". Metrics: mean
adjacent cosine, mean cosine to the end along the path (monotonicity), intra-list
diversity, and repeat-artist rate. Results go to `docs/AUDIO-BENCHMARK.md`; the method
version is accepted only if the bridge beats random on the owner judgments and is not
worse than plain neighbours on diversity. Until accepted, `not_evaluated` is returned.

## Risks / Trade-offs

- [Users take the bridge as a mix or DJ set] -> method note about tempo, key, lyrics and
  mixability; no audio; experimental label until evaluated.
- [Artist clustering: one artist fills the bridge] -> report repeat-artist rate in the
  evaluation; an artist cap is an open question rather than a hidden rule.
- [First-three-minutes bias] -> stated in every bridge.
- [Latency on large libraries] -> bounded n and measured; queued fallback documented.
- [Interpolation passes through empty regions] -> MMR still picks the closest unused
  track; adjacent cosine in the explanation shows weak steps honestly.

## Migration Plan

One Alembic migration adds `sound_bridges` with cascade from `users`. Rollback drops it.

## Open Questions

- Should endpoints include a theme centroid (from `add-sound-themes`) or a mood region?
  Mood scores live in a different space and would need their own design.
- Should there be an artist cap per bridge?
- Should the web page be split into its own `web/sound-bridge` capability?
- Are five settings the right granularity, and which is the default?
