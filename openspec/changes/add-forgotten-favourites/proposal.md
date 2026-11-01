# Proposal

## Why

The owner has about 74,826 imported listens from 2019 to 2026 (draft
`import-listenbrainz-history`). Tracks played heavily years ago and not since are an
obvious, low-risk thing to resurface, and need no audio, embeddings or GPU. The research
notes (docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md section 4, user jobs; section 6
follow-ups) and mockup 12 of docs/research/MOCKUPS.md frame this as "past favourites" from
the listener's own history. The cautions are about honesty, not models: a "favourite" here
is a play-count rule, not a love; a gap in imported history is not silence; night autoplay
inflates counts; and the same song can be split across versions and uploads.

## What Changes

- **Explicit definitions**, versioned as a product rule:
  - *Past favourite*: a track with at least N included plays (default 8) within some
    rolling peak window of W days (default 90).
  - *Forgotten*: no included play in the last M days (default 365), assessed only when
    the user's imported coverage spans those M days and the user had at least K other
    included plays (default 50) on at least D distinct days (default 20) in that window.
- **Included plays** follow the sessions' `effective_kind`: plays in sessions whose
  effective classification is autoplay are excluded by default and counted; the user can
  include them. Plays in sessions classified `unknown` (no timezone) are included and
  their count is disclosed.
- **Owner-only list** of forgotten favourites with, per track: peak window, plays in the
  peak, last included play date and total included plays; sorted by peak plays. The
  imported coverage range and the rule values are shown with the list.
- **Distinct states**: `not_imported` (no completed import), `coverage_gap` (imported
  coverage does not span the forgotten window), `insufficient_history` (too little recent
  activity to call anything forgotten), `none_found`.
- **Dismissals**: the user can hide a track from the list ("not a favourite" or "not now");
  dismissals are private, listable, deletable and removed with the account.
- **Wording guard**: never "loved", "liked" or "your favourite"; always "played a lot
  in <period>". No inferred loves, as ListenBrainz loves were not imported.
- **Owner review gate** before the list is offered beyond the owner.

Out of scope:
- ListenBrainz loved tracks/feedback import or any inferred "love" signal.
- Merging versions, remasters or duplicate uploads into one work; the list notes that
  counts may be split.
- Audio, embeddings, sound similarity ("sounds like your old favourites") or playback.
- Club or shared views, notifications, Discord DMs or scheduled prompts.
- Spotify listening history (metadata-only; not a listen source here).

## Capabilities

### New Capabilities
- `listening/rediscovery`: definitions, coverage checks, session exclusions, the
  owner-only forgotten-favourites list and page, dismissals and their deletion.

### Modified Capabilities
None. Reads `listening/listenbrainz-import` coverage and `listening/listen-sessions`
classifications without changing them.

## Impact

Current state:
- **Observed:** `docs/status.yaml` has no ListenBrainz import item; imported history
  exists only as the draft `import-listenbrainz-history`.
- **Observed:** the draft `listening/listenbrainz-import` spec records per-account import
  coverage and distinguishes `not_imported` from covered-with-zero-listens
  (`openspec/changes/import-listenbrainz-history/specs/listening/listenbrainz-import/spec.md`).
- **Observed:** the draft `listening/listen-sessions` spec classifies sessions
  `night_autoplay`, `unclassified` or `unknown`, lets users override with `keep` or
  `autoplay`, and downstream reads the effective classification
  (`openspec/changes/import-listenbrainz-history/specs/listening/listen-sessions/spec.md`).
- **Observed:** the same draft keeps ListenBrainz loved-track feedback out of scope
  (`openspec/changes/import-listenbrainz-history/proposal.md`).
- **Observed:** `apps/web/app/listening/page.tsx` is the only listening page.
- **Assumed:** listens resolve to a track id or a normalised artist/title key from the
  import normaliser; this change counts by that key and does not merge versions.

Dependencies:
- `import-listenbrainz-history` (`listening/listenbrainz-import`,
  `listening/listen-sessions`, `identity/user-preferences` for timezone).

Affected:
- `sidetrack/listening/` (rediscovery read model, dismissals table, owner-only routes),
  `migrations/`, `apps/web` (`/listening/rediscover`), `packages/api-client`.
- Docs: `docs/MODULES.md`, `docs/status.yaml`.
