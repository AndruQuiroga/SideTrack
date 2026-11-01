# Proposal

## Why

`add-sound-themes` will group a user's embedded library into candidate sound-worlds and
suggest descriptive terms from audio, and `add-weekly-listening-profile` will share each
week's included plays among them. Neither gives the listener a way to browse those
sound-worlds, see the tracks behind them, or say "this label is wrong". Mockup 11 of
docs/research/MOCKUPS.md sketches that explorer. The research notes
(docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md sections 2, 4 and 6.4) are explicit that
generated names are suggestions, prompt- and vocabulary-sensitive, and that the user's
corrections are what make them trustworthy; those corrections are personal data and need
the same export and deletion guarantees as listens.

## What Changes

- **Sound-world explorer page** at `/listening/sound-worlds`: a list-first view of the
  user's themes with their display name or suggested terms (marked as suggestions),
  representative tracks, track counts for the library, and play counts and shares of
  included plays for a selected week. Unassigned tracks and plays stay visible as
  "Other or uncertain". Two weeks can be compared side by side with their own
  denominators.
- **Theme detail**: the member tracks of a theme, and for any track its nearest
  neighbours computed in the original 512-d space within the user's eligible library,
  never from map positions.
- **Optional map link**: the taste-galaxy projection from `add-listening-visuals` can be
  opened filtered to a theme, carrying its distortion notice; the list remains the
  primary, equivalent view. No new projection is computed here.
- **Label feedback**: on a theme's suggested term or a track's suggested tag the user can
  accept ("fits"), reject ("this label is wrong") or rename (theme display name, via the
  rename defined in `add-sound-themes`). Rejected terms stop being shown as suggestions
  for that user. Verdicts carry over a theme rebuild only with sufficient membership
  overlap, otherwise they are reported as orphaned, never silently reassigned.
- **Feedback is personal data**: owner-only, listable, exportable as JSON, deletable
  singly or all, removed with the account, never visible to other members and never used
  to retrain a model or change another user's labels.
- **Distinct states**: `no_themes`, `not_enough_tracks`, `stale` (built from an older
  embedding revision or vocabulary), `not_enough_listening` for a week, `unavailable`.
- **Accessibility**: names, patterns and text rather than color alone; keyboard and
  screen-reader operation; reduced motion respected (WCAG 2.2 use of color).

Out of scope:
- Building, clustering or naming themes, and zero-shot tags (`add-sound-themes`).
- Weekly theme shares and their inclusion rules (`add-weekly-listening-profile`).
- Computing or rendering the 2-D projection (`add-listening-visuals`).
- Viewing another member's sound-worlds, sharing them, or club-wide themes.
- Using any user's feedback to retrain, recalibrate or relabel for other users; pooling
  feedback across users for evaluation (would need separate consent).
- Audio playback or audio links (ADR 0007).
- Any claim that a label is a genre fact or describes the listener.

## Capabilities

### New Capabilities
- `web/sound-world-explorer`: the `/listening/sound-worlds` page: list-first theme
  browsing with denominators, unassigned tracks, week comparison, original-space
  neighbours, the optional map link, explicit empty and stale states, and accessibility.
- `analysis/label-feedback`: a user's accept, reject and rename verdicts on generated
  labels, how they affect only that user's display, how they survive rebuilds, and their
  export and deletion.

### Modified Capabilities
None. `identity/account-deletion` and `identity/personal-data-visibility` are followed,
not changed; the new rows cascade from `users`.

## Impact

Current state:
- **Observed:** there is no theme, label or feedback code or table in `sidetrack/`
  (no `theme` or `feedback` identifiers under `sidetrack/`); themes exist only as the
  draft `add-sound-themes`, whose design names tables `sound_theme_builds`,
  `sound_themes`, `sound_theme_members` and `sound_theme_names` and a Jaccard-overlap
  rename carry-over reported as `rename_orphaned`
  (`openspec/changes/add-sound-themes/design.md`, `.../specs/analysis/sound-themes/spec.md`).
- **Observed:** `apps/web/app/listening/page.tsx` is the only listening page; there is no
  `/listening/sound-worlds` route.
- **Observed:** neighbours are ranked by exact cosine within one model, revision and
  pipeline, excluding the query's own track (`sidetrack/analysis/embeddings/neighbours.py`),
  but over all assets, not one user's library.
- **Observed:** embeddings are one pooled vector per asset over at most the first 180 s
  (`sidetrack/analysis/embeddings/audio.py`), so themes and neighbours describe at most
  the first three minutes.
- **Observed:** account deletion cascades every row tied to a user
  (`openspec/specs/identity/account-deletion`); there is no general personal-data export
  route today (no export route under `sidetrack/**/routes/`).
- **Assumed:** `add-sound-themes` exposes a stable theme lineage across rebuilds (its
  overlap carry-over) that label verdicts can reuse; task 1.1 confirms the shape before
  storage is built.

Dependencies:
- `add-sound-themes` (`analysis/sound-themes`, `analysis/text-embeddings`).
- `add-weekly-listening-profile` for weekly theme shares of included plays.
- `resolve-listens-to-audio` (`analysis/listen-audio-resolution`) for the eligible library.
- `add-listening-visuals` (`web/listening-mirror`) only for the optional map link.

Affected:
- `sidetrack/analysis/` (label-feedback tables, read models, owner-only routes),
  `migrations/`, `apps/web` (`/listening/sound-worlds`), `packages/api-client`.
- Docs: `docs/MODULES.md`, `docs/AUDIO.md` (feedback semantics), `docs/status.yaml`.
