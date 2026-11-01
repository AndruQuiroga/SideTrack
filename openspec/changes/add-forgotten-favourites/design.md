## Context

Imported ListenBrainz history (draft `import-listenbrainz-history`) gives per-user listens
with UTC times, per-account import coverage, and sessions classified `night_autoplay`,
`unclassified` or `unknown` with user overrides (`keep` / `autoplay`) and an effective
classification. Loved-track feedback is not imported. This change reads those to list
past favourites the user has not played recently. No audio or model is involved.

Cautions from docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md and docs/research/MOCKUPS.md:

- Notes section 4 (user jobs) and mockup 12: rediscovery is about the user's own history,
  shown with its time range.
- Notes section 3 and the mockup anti-patterns: denominators everywhere; gaps are not
  silence; no invented signals ("loved").
- Night autoplay inflates play counts, so exclusions must be disclosed and reversible.

## Goals / Non-Goals

**Goals:**

- Explicit, versioned rules that a user can read and that tests can pin.
- Refusal to call anything forgotten when history does not cover the recent window.
- Private, deletable dismissals.

**Non-Goals:**

- Version merging, love import, sound-based rediscovery, notifications, club views.

## Decisions

### 1. Play-count rule over a rolling peak window

Favourite = at least N included plays within any W-day window (N=8, W=90). Peak window is
the earliest W-day window with the maximum count.

- Alternative: share of all plays in a period. Rejected: punishes heavy-listening periods
  and is harder to explain.
- Alternative: all-time top-k. Rejected: biased to recent and long-imported periods and
  misses short obsessions.
- Alternative: loves. Unavailable (not imported) and must not be inferred.

### 2. Forgotten requires coverage and activity

Forgotten = no included play in the last M days (M=365), only if coverage spans those M
days and the user had at least K=50 other included plays on D=20 distinct days in them.

- Alternative: forgotten = absent from imported data. Rejected: a missing import or a
  ListenBrainz gap would masquerade as forgetting (`not_imported` is not zero listens).
- Alternative: per-track expected-rate model. Rejected for v1 as unexplainable.

### 3. Session exclusions read effective classification

Counts read each session's effective classification. Autoplay excluded by default and
counted; `unknown` included and counted; a per-request toggle includes autoplay.

- Alternative: drop `unknown` sessions. Rejected: without a timezone every session is
  `unknown`, which would empty the feature.

### 4. Identity key without version merging

Plays are grouped by the import's track key (track id where resolved, else normalised
artist and title). Versions are not merged; the page says so.

- Alternative: fuzzy title merge. Rejected: merges remixes and live versions wrongly; a
  separate version-discovery change can address it.

### 5. Computed on read

The list is a SQL aggregate over the user's listens per request (tens of thousands of
rows); no cache table.

- Alternative: nightly materialisation. Rejected: no scheduler need and staleness.

### 6. Dismissals table

`rediscovery_dismissals(id, user_id FK users ON DELETE CASCADE, track_key, reason
not_a_favourite|not_now, created_at)`, unique on (user, track_key).

### 7. Owner review gate

The owner reviews their own list against memory (how many listed tracks are real past
favourites, how many are autoplay or duplicate artefacts) and records the result and any
rule changes in `docs/LISTENING.md` (or the existing listening doc) before the page is
linked in navigation for other users.

## Risks / Trade-offs

- [Autoplay or a looped album inflates counts] -> default exclusion, disclosed counts,
  owner review of the rule.
- [Version splits hide a favourite] -> stated limit; follow-up change.
- [Imports with gaps] -> `coverage_gap` and `not_imported` states; never zero-fill.
- [Thresholds wrong for light listeners] -> values returned and versioned; owner review;
  open question on per-user tuning.

## Migration Plan

One Alembic migration adds `rediscovery_dismissals` with a cascade from `users`. Rollback
drops it.

## Decisions on earlier open questions

- The defaults stay N=8, W=90, M=365, K=50 and D=20, and users can't adjust them yet.
- `not_now` dismissals don't expire. The user clears them.
- The owner's review is recorded in `docs/LISTENING.md`.
