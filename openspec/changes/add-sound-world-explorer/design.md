## Context

Mockup 11 (docs/research/MOCKUPS.md) sketches a sound-world explorer: themes with
representative tracks, unassigned plays, a week comparison and a way to correct labels.
The data comes from other drafts: themes and suggested terms from `add-sound-themes`,
weekly theme shares from `add-weekly-listening-profile`, the eligible library from
`resolve-listens-to-audio`, and the optional map from `add-listening-visuals`. This change
adds the browsing surface and the user's corrections.

Evidence and cautions carried from docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md:
- Section 1: one pooled vector per asset over the first 180 s; window vectors are not
  stored, so labels describe at most the first three minutes.
- Section 2: neighbours must come from the original space; 2-D projections distort
  distances and cluster sizes (UMAP/t-SNE caveats).
- Section 4 "Visual vocabulary and accessibility": no color-only meaning (WCAG 1.4.1),
  list alternative for every chart, denominators everywhere, abstention over invented
  names.
- Section 6: generated names are prompt and vocabulary sensitive; user correction is the
  trust mechanism, and corrections are personal data.

## Goals / Non-Goals

**Goals:**
- A list-first, accessible explorer of one user's own sound-worlds with denominators.
- Neighbours from the original space within the user's eligible library.
- Accept, reject and rename feedback that only affects the owner's display, survives
  rebuilds conservatively, and can be exported and deleted.

**Non-Goals:**
- Building themes, tags or projections; club or shared views; training on feedback;
  pooling feedback across users; audio playback.

## Decisions

### 1. List-first page, map only as a link
The explorer is a list; the map from `add-listening-visuals` is linked, filtered to a
theme, with its distortion notice.
- Alternative: an embedded interactive scatter as the main view. Rejected: projection
  distortion (notes section 2) and accessibility (section 4) make a map a poor primary
  interface, and it would duplicate `web/listening-mirror`.
- Alternative: compute a theme-specific projection here. Rejected: a second projection
  pipeline for little gain.

### 2. Neighbours queried per request within the eligible library
Neighbours use exact pgvector cosine (as `neighbours.py` does today), restricted to the
user's eligible assets of the current model, revision and pipeline. With hundreds to a few
thousand vectors per user, exact search is cheap; no index or cache is added.
- Alternative: precompute k-NN per asset. Rejected until latency shows a need; it would
  go stale on every new embedding.
- Alternative: reuse global `similar_assets`. Rejected: it is not user-scoped and would
  leak tracks from other libraries.

### 3. Verdict storage keyed by stable targets
Table `label_feedback(id, user_id FK users ON DELETE CASCADE, target_kind theme|asset,
theme_lineage_id NULL, asset_id NULL, term, vocabulary_version, verdict
accepted|rejected, status active|orphaned, created_at, updated_at)` with uniqueness on
(user, target, term). Theme verdicts key on the theme lineage that `add-sound-themes`
carries across rebuilds (membership Jaccard >= 0.5, the same rule as renames); asset
verdicts key on (asset, term).
- Alternative: key on build-specific theme ids. Rejected: every rebuild would orphan
  every verdict.
- Alternative: re-attach by label text. Rejected: two different themes can share a term,
  so verdicts would move to the wrong group.

### 4. Feedback filters display only
Rejected terms are filtered at read time for that user. Stored scores, thresholds and the
vocabulary are not touched.
- Alternative: per-user threshold adjustment or few-shot recalibration. Rejected: it
  makes model output depend on private feedback, is hard to evaluate, and blurs
  "suggestion" with "fact".

### 5. Export as part of label feedback, not a general export
`GET /me/label-feedback/export` returns JSON of verdicts and renames. No general
personal-data export exists today; this change does not invent one.
- Alternative: build a general export first. Rejected as scope creep; record as a
  follow-up.

### 6. Owner evaluation gate before label claims
Before the explorer presents terms to users, the owner reviews a sample of themes and
tags (blind accept/reject rate) and records the result in `docs/AUDIO-BENCHMARK.md`. Until
accepted, the label method panel says labels are unevaluated.

## Risks / Trade-offs

- [Rebuild orphans many verdicts] -> orphaned verdicts are listed for review, not lost or
  silently moved.
- [Users read suggested terms as facts] -> "suggested" marking, abstention, method panel
  and three-minute note.
- [Week shares misread as percentages of all listening] -> denominator is "included plays
  with usable audio", always shown, and unassigned plays stay visible.
- [Neighbour query slow for large libraries] -> bounded k=10; measure in the integration
  test; precomputation is the documented fallback.
- [Theme lineage shape differs from assumption] -> task 1.1 confirms against
  `add-sound-themes` before storage is built.

## Migration Plan

One Alembic migration adds `label_feedback` with a cascade from `users`. No backfill.
Rollback drops the table; themes are unaffected.

## Open Questions

- Should asset-tag suggestions be shown only inside the explorer (as `add-sound-themes`
  proposes) or also on track pages?
- Should "accepted" terms be visually promoted or only marked?
- Should a general personal-data export be its own change that this one later joins?
- The weekly profile draft is being rewritten; the capability name used for week shares
  may change.
