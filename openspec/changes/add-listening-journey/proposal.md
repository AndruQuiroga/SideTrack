# Proposal

## Why

"How did my listening change?" is one of the user jobs the research notes name (section
4), and mockup 12 sketches the answer as a journey of listening eras. The notes are
cautious about it (section 2, "Listening eras and richer emotional language"):

- Compare eligible listening windows using play-weighted or track-level summaries, and
  show the tracks behind any proposed shift.
- Offline change-point tools such as ruptures offer candidate methods, but the method and
  cost function decide what kind of change is found.
- Compare against a simple rolling-window baseline, and test stability under coverage
  gaps, repeat plays and parameter changes.
- An algorithmic boundary is not a life event, and a missing period is not a zero-valued
  period.

Without these rules a timeline would invent turning points from import gaps or one
looped album.

## What Changes

- **A weekly signal per user**: for each week that is eligible under the weekly profile's
  rules, a play-weighted and an equal-track centroid of the current MuQ-MuLan embeddings
  over included plays with usable audio, plus an artist-share vector as a metadata
  comparison. Ineligible weeks, `not_imported` spans and weeks below the sample minimum
  are gaps, never zeros.
- **Offline candidate shift detection** with a ruptures-based change-point search,
  reported next to a rolling-window baseline (before/after distance with a fixed window).
  A candidate is reported only if both agree within a tolerance.
- **Stability checks** for every candidate: week dropout, collapsing repeated plays, and a
  parameter sweep. Each candidate gets a stability fraction, and unstable candidates are
  not shown.
- **Gap boundaries**: a run of missing or ineligible weeks above a length splits the
  timeline into segments. Detection never runs across a gap, and the gap is shown as
  missing history.
- **Evidence for each shift**: the tracks whose play share changed most between the
  before and after windows, with play counts, plus most-played tracks for each era.
- **Hypothesis wording**: the result is "an estimated change in your analyzed listening",
  never a life event, mood, cause or diagnosis.
- **An evaluation gate**: eras are a user-facing claim under
  `add-music-analysis-evaluation-protocol`. Until the `listening-eras` entry is
  `approved`, only the owner sees results, labelled unvalidated, and other readers get
  `gate_pending`.
- **A `/listening/journey` page** (mockup 12) showing segments, gaps, candidate shifts
  with their tracks, period comparison and coverage.

Out of scope:
- "Tracks played again after a long break" (mockup 12's third line). This needs its own
  definition of "forgotten" over import coverage (notes section 4). It is drafted
  separately as `add-forgotten-favourites`.
- Mood or theme eras. Signals use embeddings and artist shares only. Mood axes may be
  added once `add-track-mood-scores` passes its gate.
- Inferring feelings, life events or causes, and any GEMS-based inference (notes
  section 2).
- Club or public visibility of eras. They are owner-only in this change.
- Playing or serving audio.

## Capabilities

### New Capabilities
- `analysis/listening-eras`: weekly signal, candidate shift detection against a
  rolling-window baseline, stability checks, gap handling, evidence tracks, and the
  gate-dependent read model.
- `web/listening-journey`: the owner's journey page with segments, gaps, candidate shifts,
  evidence tracks and period comparison.

### Modified Capabilities
None.

## Impact

Depends on:
- `add-weekly-listening-profile`: `analysis/weekly-listening-profile`, for week
  boundaries in the user's timezone, `timezone_missing`, included plays, the 20-play
  minimum and `not_enough_listening`.
- `import-listenbrainz-history`:
  - `listening/listen-sessions`: `effective_kind`, which keeps `night_autoplay` sessions
    out.
  - `listening/listenbrainz-import`: per-account import coverage and `not_imported`.
- `resolve-listens-to-audio`: `analysis/listen-audio-resolution`, for `audio_for_track`
  with status `ok`.
- `add-music-analysis-evaluation-protocol`: the `listening-eras` gate entry, using the
  `eras` record type.
- Nice to have: `add-audio-coverage-review`, which the coverage link points to.

Current state:
- **Observed:** production stores one 512-d MuQ-MuLan vector per asset, pooled over at
  most the first 180 s (`sidetrack/analysis/embeddings/registry.py`), and no HTTP route
  uses embeddings (docs/STATUS.md).
- **Observed:** no era, timeline or change-point code exists under `sidetrack/`, and
  `ruptures` is not a dependency (`pyproject.toml`).
- **Observed:** `/listening` shows recent listens only (`apps/web/app/listening/page.tsx`).
- **Assumed:** the owner's history spans enough eligible weeks to evaluate the method.
  Production holds 862 embedded assets, but how much listening history is eligible is
  not yet measured.
- **Assumed:** ruptures (BSD-2-Clause) is a pure-Python/NumPy worker dependency. It needs
  no new service.

Affected:
- `sidetrack/analysis/` (eras module, job, tables, routes)
- `migrations/`
- `pyproject.toml` / `uv.lock` (worker extra adds `ruptures`)
- `apps/web/app/listening/journey/`
- `packages/api-client`
- `services/audio-lab` (eras evaluation command)
- `docs/AUDIO.md` and `docs/status.yaml`
