# Design

## Context

See proposal.md. Sources:
- Mockup 12 in `docs/research/MOCKUPS.md` and its anti-patterns.
- Notes section 2, "Listening eras and richer emotional language".
- Notes section 3, the validation protocol. Eras use the `eras` record type defined in
  `add-music-analysis-evaluation-protocol`.
- Notes section 4: user jobs, and "a missing period is not zero".

Constraints:
- Postgres is the only stateful service, and jobs use the existing Postgres queue.
- PyTorch stays out of the root lock (ADR 0004). This change needs no model inference,
  because it reads stored vectors only.
- Production stores one pooled vector per asset, covering at most the first 180 s, so
  within-track change is invisible.
- Week eligibility, timezone and included plays come from
  `analysis/weekly-listening-profile`. Inclusion comes from `effective_kind`.

## Goals / Non-Goals

**Goals:**
- Candidate shifts that survive a simple baseline and perturbation tests.
- Each shift comes with the evidence tracks behind it.
- Gaps are honest.

**Non-Goals:**
- Resurfacing forgotten tracks.
- Mood or theme eras.
- Naming eras.
- Club visibility.
- Real-time updates.

## Decisions

### D1. Signal: weekly centroids plus artist shares
- **Choice.** The detection input is the play-weighted centroid, L2-normalised, of
  current embeddings over each eligible week. An equal-track centroid and an
  artist-share vector are stored as diagnostics.
  - If the play-weighted and equal-track signals disagree, repeat-driven shifts become
    visible (notes section 2 recommends comparing both).
  - The artist-share vector shows whether a sonic shift is really an artist shift.
- **Alternatives.**
  - Per-play sequences: noisy and expensive.
  - A 2-D projection: distorted (notes section 2).
  - Mood axes: not gated yet.

### D2. Detector: ruptures, offline, with a cosine-distance cost
- **Choice.** Use ruptures PELT with an `rbf` or `cosine` cost and a BIC-style penalty,
  run on the worker. The cost and penalty are set by the evaluation record, not tuned per
  user.
- **Alternatives.**
  - Hand-written binary segmentation: more code, and less well tested.
  - Bayesian online change-point detection: we only need offline detection, and its
    priors are harder to explain.
- ruptures is BSD-2-Clause and depends on NumPy, which is already pinned. It is a library
  dependency, not infrastructure, so it needs no ADR.

### D3. Baseline and agreement rule
- **Choice.** The baseline is the cosine distance between the means of the 8 eligible
  weeks before and the 8 after, flagged at local maxima above a fixed threshold. A
  candidate needs both the detector and the baseline within 2 eligible weeks of each
  other. This follows the notes ("compare against a simple rolling-window baseline").
- **Alternative.** Report the detector alone. Rejected: that leaves no check against a
  method artefact.

### D4. Gaps
- **Choice.** Weeks that are `not_imported`, `not_enough_listening`, or affected by
  `timezone_missing` are gaps.
  - A run of 8 or more gap weeks splits segments.
  - Shorter runs are dropped from the input, not interpolated.
- **Alternative.** Interpolate across gaps. Rejected: it fabricates data (notes
  section 3, step 3).

### D5. Stability
- **Choice.** Run 20 variants in total:
  - Random 10% week dropout.
  - Repeat-collapsed input.
  - A penalty sweep at ×0.5, ×1 and ×2.
  - The equal-track signal.
- A candidate needs a stability of at least 0.7. The thresholds are product rules,
  versioned with `ERAS_VERSION`, and are revisited by the gate.

### D6. Storage and job
- **Tables.** Add `listening_era_runs` and `listening_era_items`:
  - `listening_era_runs`: user, version, embedding model/checkpoint/pipeline,
    parameters, and status.
  - `listening_era_items`: segments, gaps, candidates, stability, and evidence track
    IDs with counts.
- **Ownership and lifecycle.** Both tables are owned by the analysis domain, and account
  deletion cascades to them.
- **Job.** The job runs weekly on the Postgres queue, and on demand after an import or
  timezone change. Reads compare the stored versions with the current ones, which yields
  `stale_model`.

### D7. Routes and gate
- **Routes.** `GET /users/{id}/listening/eras` and
  `GET /users/{id}/listening/eras/candidates/{cid}`.
- **Access.** Owner-only; everyone else gets 404.
- **Gate status.** Read from the evaluation register (`docs/evaluations/register.yaml`),
  where it is bundled at build time.

### D8. Page
- **Layout.** `/listening/journey` is a horizontal segment and gap timeline, with a text
  list as the accessible primary representation.
- **Content.** It shows a compare-periods selector, an "unvalidated" notice, and a link
  to `/listening/coverage`.

## Risks / Trade-offs

- **Thresholds such as 8, 16, 0.7 and 2 weeks are chosen before evaluation.** They are
  versioned product rules, and the gate record must test them on the owner's history.
- **The 180 s cap hides change within a track.** This is stated in the coverage link.
  Eras describe the analyzed audio only.
- **Users may still read a candidate as a life event.** The wording is a fixed label,
  there is no free-text field, and a guard test checks for causal words.
- **The owner's history may be too short to validate the method.** In that case the
  status remains `insufficient_history`, and the gate remains `gate_pending`.

## Migration Plan

An additive migration creates both tables. There is no backfill: the first job run
computes the results. To roll back, drop the tables and remove the route.

## Open Questions

- Which ruptures cost should be used (`rbf` or `cosine`), and how should the penalty be
  calibrated on the owner's history? The gate record decides.
- Should monthly granularity be offered for sparse listeners?
- What exactly defines "tracks played again after a long break"? This belongs to a
  follow-up change.
