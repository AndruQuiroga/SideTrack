# Design

## Context

See proposal.md for motivation. The protocol is section 3 ("A practical validation
protocol") of `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md`; the dataset rights come
from that section's table; the model cautions from section 2; the user jobs and honest
states from section 4. Constraints that shape the approach:

- `services/audio-lab` is the benchmark CLI with its own lock and PyTorch (ADR 0004);
  production code must not import it, and it must not read the production database.
- The model-selection benchmark (`analysis/audio-benchmark`) is being extended on
  `add-mood-probe-benchmark`. This change must not collide
  with that delta.
- Personal benchmark data already has to stay outside the repo (`analysis/benchmark-seeds`).
- `docs/status.yaml` is the source of truth for what works, regenerated into
  `docs/STATUS.md` by `scripts/gen_status.py`, and checked in CI.

## Goals / Non-Goals

**Goals:**
- One reusable, checkable definition of "good enough to show a user" for any analysis claim.
- Make the absence of evidence visible (`gate_pending`, `incomplete`, `not_covered`, `stale`)
  instead of letting a strong-looking dataset score stand in for it.
- Record dataset rights once, with their gaps, before anyone downloads anything.

**Non-Goals:**
- Running evaluations or choosing thresholds for specific features; each feature's change
  owns its numbers and records them in its gate.
- Product enforcement code (routes, pages); feature changes read their gate status.
- Statistical method selection beyond requiring the sampling unit to be stated.

## Decisions

### D1. A new capability `analysis/evaluation-gates`, not a modification of `analysis/audio-benchmark`

`analysis/audio-benchmark` specifies the model-selection CLI (embed, report, duels, parity,
score). The gate governs product claims built on whichever model it selected, including
claims that need no new embedding (eras, timing). Keeping it separate avoids a conflicting
delta with `add-mood-probe-benchmark`, which modifies `analysis/audio-benchmark`.
- *Alternative:* add requirements to `analysis/audio-benchmark`. Rejected: mixes model
  choice with product truthfulness and collides with the in-flight mood-probe delta.

### D2. Evidence lives in three places with different privacy

| Artifact | Location | Content |
| --- | --- | --- |
| Evaluation record (`record.json`) | Outside the repo, next to the audio-lab run (HDD) | Full record including per-item results and examples |
| Gate summary (`summary.json`) | `docs/evaluations/summaries/<claim>/<record-id>.json` | Aggregates, counts, flags; no titles, paths or per-track values |
| Register (`register.yaml`) and rights register (`datasets.yaml`) | `docs/evaluations/` | One entry per claim; one entry per dataset |

`audio-lab gate summarize` produces the summary from the record and refuses to include
string fields other than an allow-list (claim, revisions, metric names, flags).
- *Alternative:* store records in Postgres. Rejected: evaluation is offline lab work; the
  production DB must not depend on audio-lab, and records hold dataset annotations that
  must not enter backups shared with the app.

### D3. Record schema is task-typed

A record has a common header (task, claim wording, model, checkpoint, probe/head revision,
pipeline, vocabulary version, preprocessing, preview/full, analyzed duration, time range,
population counts, date, datasets cited) and a task section, one of `neighbours`,
`text_label`, `mood`, `timing`, `eras`, `other`. Each task type has a required-fields list
taken from notes section 3 step 2. `other` requires a free-text metric plan and is never
`complete` without one; this keeps unforeseen claims from slipping past.
- *Alternative:* a single generic metrics map. Rejected: completeness could not be checked.

### D4. Two checkers, one per boundary

- `audio-lab gate check|summarize` (inside audio-lab) validates a record and writes a summary.
- `scripts/check_evaluations.py` (stdlib + PyYAML only, like `gen_status.py`) validates the
  registers, the committed summaries, revision staleness against each feature's declared
  revisions, and the cross-check with `docs/status.yaml`. It runs in CI next to the status
  staleness check.
- *Alternative:* a single checker in audio-lab. Rejected: CI for the root package should
  not install audio-lab's PyTorch stack.

### D5. Status and staleness rules

`approved` requires a complete summary, an owner `approve` decision and every cited dataset
registered for that use. A register entry declares `feature_revisions` (model, checkpoint,
probe, pipeline, vocabulary); a feature change copies its live values into the entry when
it ships. A mismatch with the summary's revisions is `stale`. Production gating reads only
the status string; the claim is shown when `approved` and otherwise renders its own
documented unavailable state.

### D6. Owner gate format

The owner reviews a small, stratified example set (including held-out obscure, electronic
and altered items) in an offline HTML page like the existing duel report (no network
scripts, no HTTP audio service; local files only), and exports `decision.json`
(`approve` / `reject` / `correct`, notes, corrections). Corrections are kept so a later
record can measure them.

### D7. Rights register content

Seeded from notes section 3: DEAM, MusAV, MTG-Jamendo, PMEmo, MusicCaps, Song Describer,
MuChoMusic, Jam-ALT, Harmonix Set. Each entry records: URL, use, `audio_terms`,
`annotation_terms`, `status` per use (`recorded`, `rights_unconfirmed`, `annotation_only`,
`not_for_use`), gaps (for example MusAV previews "non-commercial scientific research on
request"; MTG-Jamendo sizes 46 GB / 156 GB exceeding the 40 GB SSD budget, so HDD only;
MusicCaps and Harmonix audio only via YouTube references, so `annotation_only`), the
acquisition method (`owner_manual`, never automated yt-dlp), storage (`HDD outside repo`)
and `reviewed: 2026-10-31`. DEAM's original site was inaccessible during review, so its
audio entry starts `rights_unconfirmed` until the owner confirms the files' terms.

## Risks / Trade-offs

- [Gate becomes paperwork that blocks everything] → Feature changes may ship their
  pipelines and owner-only experimental views while `gate_pending`; only user-facing claims and
  `works` statuses are gated.
- [Owner is the only rater, so judgments reflect one listener] → Records state rater
  count; a one-rater gate approves the claim for the owner's library only, and the
  summary says so. Club-wide claims need a separate entry.
- [Thresholds chosen after seeing results] → The schema requires material-change
  thresholds and tolerances to be declared in a record committed before scoring
  (`declared_at` earlier than `scored_at`).
- [Rights entries go stale as sites change] → `reviewed` date and a CI warning after 365 days.
- [Summary leaks personal data] → Allow-list serialisation plus a test that fails on any
  title or path in a summary.

## Migration Plan

Docs and tooling only. Seed `register.yaml` with existing evidence: MuQ-MuLan neighbours
(`incomplete`: benchmark duels exist, run `20261027-031711-c7c3698`, but no random control,
coverage or robustness record for the production pipeline) and the mood probe
(`gate_pending`: run `20261031-204732-9b07ff0`, not artist-grouped, owner gate pending).
Rollback is deleting `docs/evaluations/` and the CI step.

## Open Questions

- Which feature-owned file holds `feature_revisions` once features ship (register entry
  vs. a constant the check imports)? Either satisfies D5; decide in the first feature
  change that becomes user-facing.
- Whether a 365-day rights review interval is right; it changes only a CI warning.
