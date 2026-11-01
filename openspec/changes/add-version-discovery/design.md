# Design

## Context

See proposal.md. Evidence: docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md section 2 (tools
table: Chromaprint targets near-identical audio; MOVE and CoverHunter target version
retrieval, not proof of the same recording; their terms, dependencies and accuracy need
separate review) and section 6 item 2 (exact-looking matches can still conflate versions;
do not equate sonic similarity with recording identity). docs/research/MUSIC-ANALYSIS.md
idea 4: the MuQ preview benchmark does not justify automatically merging slowed or sped-up
edits.

Constraints: 862 production assets; GTX 1070 (8 GB, sm_61, fp32) shared and serial on the
`gpu` queue (ADR 0010); Postgres is the only stateful service; audio never served over HTTP.

## Goals / Non-Goals

**Goals:**
- Cheap, local, explainable near-identical candidates with evidence.
- A measured view of how each method fails on speed edits and hard negatives.
- A review record the operator controls, with no side effects.

**Non-Goals:**
- Acting on confirmed relations (deduplication, links, stats).
- User-facing UI; club members reviewing each other's audio.

## Decisions

### Decision 1: Store raw fingerprints; compare locally

`asset_fingerprints(asset_id -> audio_assets CASCADE, method_version, duration_s,
fingerprint int[], state, error, created_at)`. `fpcalc -raw` runs in the default worker
image (the `audio` extra already needs it for verification). Comparison follows the
standard Chromaprint approach: an inverted index from 32-bit values (with the low bits
masked) finds pairs sharing enough values, then a bit-error-rate alignment over offsets
gives score, offsets and matched duration. With 862 assets this runs in seconds to minutes
on CPU; exact timing is measured in task 3.3.

Alternatives: AcoustID lookups to group by AcoustID ID (rejected: needs the network, about
half the tracks are unknown there, and private files would be fingerprinted against a
public service more than verification already does); comparing every pair directly
(rejected as unnecessary once the index exists).

### Decision 2: Separate candidate and relation tables

`version_candidates(id, asset_a, asset_b, kind, method, method_version, score, evidence
jsonb, status unreviewed|confirmed|rejected, decided_by, decided_at)` with
`asset_a < asset_b` and a unique key on `(asset_a, asset_b, kind, method_version)`.
Confirming sets the status and writes `version_relations(asset_a, asset_b, relation,
candidate_id, ...)`. Evidence is frozen at decision time. Relations are directional for
`preview_of`, `edit_of`, `remix_of` and `cover_of` (the CLI asks which side is the source).

Alternative: a single table with a relation column. Rejected: candidate rows are
regenerated per method version while decisions must survive regeneration.

### Decision 3: Learned methods stay in audio-lab until gated

MOVE, CoverHunter and MuQ (ADR 0010 names MuQ for recognition) run only in
`services/audio-lab` (PyTorch stays out of the root lock). A method enters production only
with a recorded run, a license and dependency record, the owner's decision and an ADR,
following ADR 0004. MuQ-MuLan pooled similarity is a hard-negative source in the benchmark,
never a candidate source.

### Decision 4: Benchmark design

Positives: the owner's preview/full pairs (from asset kind and seed identity) and synthetic
alterations of manifest assets: pitch-preserving stretch at 0.9x/1.1x/1.2x, resampled speed
change at 0.8x/0.9x/1.1x/1.25x (the common "slowed"/"sped up" edits), 15 s trims and a low
bitrate re-encode. Negatives: same-artist different-song pairs and each asset's top
MuQ-MuLan neighbours that are different songs. Real covers and remixes in the owner's
library are labelled by the owner where known; that set is small and reported with n.
Altered audio lives in the run directory outside the repo.

Alternative: public cover datasets (SHS100K, Da-TACOS). Deferred: SHS100K audio comes from
YouTube (yt-dlp is personal-only and never scheduled), and Da-TACOS ships precomputed
features rather than audio; whether any is usable is an open question.

## Risks / Trade-offs

- [Chromaprint misses speed edits] -> expected; measured per level, and those pairs wait for
  a gated learned method rather than a looser threshold.
- [Threshold too loose creates noise for the reviewer] -> thresholds are chosen from the
  hard-negative rate in the run and recorded with the method version.
- [Operator mistakes] -> every decision is reversible and keeps its evidence.
- [Relations tempt someone to merge stats] -> the spec forbids side effects; using relations
  needs its own change.

## Migration Plan

Additive migration; run `fingerprint` then `candidates` from the operator CLI. Rollback:
drop the three tables; nothing else references them.

## Open Questions

- Which learned method, if any, to gate first, after the benchmark.
- Whether club members' own uploads (if ever allowed) should be compared at all.
- Whether any public version dataset is usable without YouTube audio.
