# Design

## Context

See proposal.md for motivation. The source is mockup 10 in `docs/research/MOCKUPS.md` and
sections 1, 3 (step 3, "coverage and failure reporting") and 4 (autoplay and honest
states) of `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md`. Constraints:

- Sessions, overrides and `effective_kind` belong to `listening/listen-sessions`
  (`import-listenbrainz-history`); import coverage and `not_imported` belong to
  `listening/listenbrainz-import`.
- Links, evidence, the `ambiguous` flag, `audio_for_track` and the link coverage reasons
  (`no_link`, `ambiguous`, `no_embedding`, `file_missing`) belong to
  `analysis/listen-audio-resolution` (`resolve-listens-to-audio`).
- Domain packages expose public operations and read models and never write another
  domain's tables (`docs/MODULES.md`, `lint-imports`).
- Postgres is the only stateful service; jobs run on the existing Postgres queue.
- Embedding failures are only in job results today and jobs are cleaned up
  (`sidetrack/analysis/embeddings/jobs.py`).

## Goals / Non-Goals

**Goals:**
- One honest denominator per user, period and facet, reconciling exactly with total plays.
- Distinguish every reason a play is not analyzed, including durable failures.
- Let the owner review sessions, and operators review links, from where the gap is visible.

**Non-Goals:**
- New session rules or link matching; acquiring or serving audio; club-visible coverage;
  check-in export/delete.

## Decisions

### D1. Build on the resolution coverage operation
The `embedding` facet reuses the resolution capability's per-user coverage and its
reasons, mapping `ok` to `full_usable`/`preview_usable` by asset kind, `no_embedding` and
`file_missing` to `linked_not_usable`, and `no_link`/`ambiguous` to `no_confident_link`.
Other facets layer "has a current result for this facet" on top.
*Alternative:* an independent query over listens and assets. Rejected: two definitions of
"linked" would drift.

### D2. Inclusion is `effective_kind` only
A play is excluded exactly when its session's `effective_kind` is `night_autoplay`;
`unclassified` and `unknown` are included and disclosed. *Alternative:* also exclude
`unknown`. Rejected: users without a timezone would silently lose all plays; instead the
report states `timezone_missing`.

### D3. `not_imported` spans come from import coverage
Spans outside every linked account's import coverage are reported as `not_imported` and
excluded from all counts (notes section 4: a missing period is not zero).

### D4. Durable analysis outcomes
New table `analysis_outcomes` (asset_id, facet, model, checkpoint_revision, pipeline,
status `ok|failed`, reason, attempted_at), written by analysis jobs, owned by the analysis
domain, with an Alembic migration. `stale_model` is derived by comparing stored results
with the facet's current revisions. *Alternative:* keep job rows. Rejected: jobs are
cleaned up by design.

### D5. Routes and permissions
`GET /users/{id}/listening/coverage?start&end&facet`, `GET .../coverage/tracks?state`,
`GET .../coverage/review/sessions`, `GET .../coverage/review/links`. Session overrides and
link confirm/reject call the dependency operations' routes; this change adds no write path
of its own. Non-owners get 404; unknown facets 422; unimplemented facets
`facet_unavailable`. The API client is regenerated.

### D6. Page
`/listening/coverage` in `apps/web` renders the API only, with text state labels, tables
and the model/revision/pipeline/gate line per facet (gate status from the evaluation
register, `add-music-analysis-evaluation-protocol`).

## Risks / Trade-offs

- [Dependency specs still being amended] → Map only the final terms listed above; tasks
  start after both dependencies are applied.
- [Bucket drift between report and page] → A reconciliation invariant test
  (buckets = included; included + excluded = total) on generated data.
- [Overrides change historical weeks] → Expected; reports are computed at read time and
  state the rule version.
- [Operator-only link review may frustrate owners] → Owners still see evidence and the
  reason; link authority stays with the resolution capability.

## Migration Plan

Additive migration creating `analysis_outcomes`; backfill none (existing failures were
never stored and appear as `not_computed` until retried). Rollback drops the table.

## Open Questions

- Should owners (not only operators) be allowed to reject a link on their own tracks?
  Depends on the resolution capability's final permission model.
- Minimum sample for period aggregates per facet beyond the weekly profile's 20 plays.
- Where the check-in export/delete link goes once `analysis/mood-check-ins` lands.
