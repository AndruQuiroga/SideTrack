# Proposal

## Why

Every audio-derived statistic Sidetrack plans to show rests on a subset of plays: those
with a confident link to an audio asset, a current analysis for the facet in question,
and a session whose `effective_kind` is not `night_autoplay`. The research notes require that coverage,
unresolved links, preview/full status, analyzed duration and excluded sessions be visible
and correctable before any library-wide claim is made (notes sections 1, 3 step 3 and 4;
mockup 10). Today nothing shows a person what their numbers rest on, and analysis
failures are not even stored.

## What Changes

- **A coverage read model** for a user and a period: total plays, plays excluded because the session's
  `effective_kind` is `night_autoplay` (with the rule kind and any `keep`/`autoplay`
  override), and included plays split into exactly four buckets that sum to the included total: full asset with
  usable analysis, preview-only with usable analysis, linked audio without the facet's
  current analysis, and no confident audio link (broken down into `no_link` and `ambiguous`). Periods outside the user's import coverage are reported `not_imported`, never as zero listens.
- **Per-facet denominators.** Coverage is computed for a named facet (`embedding` now;
  `mood`, `theme` and later facets when their changes land), never one number for all.
- **Per-track analysis state** with distinct values: `available`, `no_audio`,
  `ambiguous`, `file_missing`, `not_computed`, `stale_model`, `failed`; and `insufficient_sample`
  for period aggregates. A plausible default is never substituted.
- **Analyzed duration and source** for each included track: full or preview, and the
  seconds analyzed (for example "first 03:00 of 05:12").
- **Stored analysis outcomes**, so a decode or model failure is reported as `failed`
  with its reason instead of looking like "not computed".
- **Review queues**: `night_autoplay`, `unclassified` and `unknown` sessions the user
  can set a `keep` or `autoplay` override on, and `no_audio` or `ambiguous` tracks with
  their link evidence, which operators can confirm or reject through the resolution
  operations. Audio similarity never proposes or creates a link. Every change updates the counts.
- **A `/listening/coverage` page** (owner only) presenting all of this with model,
  revision and pipeline details, accessible tables and explicit unavailable states.

Out of scope:
- Acquiring audio. No control on this page queues acquisition or yt-dlp; it lists what is
  missing.
- Playing or serving audio. Responses and pages carry no audio, file paths or stream URLs.
- Defining session classification rules or link matching; those belong to
  `import-listenbrainz-history` and `resolve-listens-to-audio`.
- Check-in export and deletion (mockup 10's last line); that belongs to the check-in
  capability in `add-weekly-listening-profile`, and this page links to it only once it exists.
- Club-visible coverage. Coverage and review are owner-only regardless of
  `listening_visibility`.

## Capabilities

### New Capabilities
- `analysis/audio-coverage`: per-user, per-period, per-facet coverage of plays by usable
  audio analysis, per-track analysis state, analyzed duration, stored analysis outcomes
  and the review queues that change them.
- `web/listening-controls`: the owner's coverage and listening-controls page, where
  coverage is shown and sessions and links are reviewed.

### Modified Capabilities
None.

## Impact

Depends on:
- `import-listenbrainz-history`: `listening/listen-sessions` (sessions with kinds
  `night_autoplay`/`unclassified`/`unknown`, `keep`/`autoplay` overrides and `effective_kind`);
  `listening/listenbrainz-import` (per-account import coverage and `not_imported`).
- `resolve-listens-to-audio`: `analysis/listen-audio-resolution` (links with method,
  confidence, evidence and an `ambiguous` flag; `audio_for_track` statuses
  `ok`/`no_audio`/`ambiguous`/`no_embedding`; operator confirm/reject; coverage reasons
  `no_link`/`ambiguous`/`no_embedding`/`file_missing`, which this change builds on).
- `add-music-analysis-evaluation-protocol`: coverage counts feed gate records; this page
  shows facet gate status next to each facet.

Current state:
- **Observed:** `audio_assets` stores `kind` (full or preview) and `duration_s`;
  `audio_embeddings` stores `model`, `checkpoint_revision` and `pipeline`
  (`sidetrack/analysis/models.py`).
- **Observed:** full tracks are embedded over at most their first 180 s
  (`MAX_FULL_S = 180.0`, `PIPELINE = "w10-t3-cap180-fp32-mean-l2-v1"` in
  `sidetrack/analysis/embeddings/registry.py`; `jobs.py` applies the cap to full assets only).
- **Observed:** an undecodable asset is reported only in the job's result as
  `decode_failed` (`sidetrack/analysis/embeddings/jobs.py`), and finished jobs are cleaned
  up (`AudioEmbedding.job_id` comment), so failures are not durably stored.
- **Observed:** `/listening` renders recent listens from stored records with UTC labels
  and makes no completeness claim (`openspec/specs/web/listening-history`,
  `apps/web/app/listening/page.tsx`); no page shows audio coverage.
- **Observed:** no HTTP route uses embeddings (docs/STATUS.md, "Audio embeddings").
- **Assumed:** the dependency changes will expose session override and link
  confirm/reject as public operations of the listening and analysis domains; this change calls
  them rather than writing their tables (docs/MODULES.md boundaries).

Affected:
- `sidetrack/analysis/` (coverage read model, analysis outcomes table, routes),
  `migrations/` (analysis outcomes), `apps/web/app/listening/coverage/`,
  `packages/api-client` (regenerated), docs (`docs/AUDIO.md`, `docs/status.yaml`).
