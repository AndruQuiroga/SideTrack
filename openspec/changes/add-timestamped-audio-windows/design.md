# Design

## Context

See proposal.md (Why, Impact). Evidence: docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md
section 1 (pipeline, 180 s cap, window vectors not stored, storage arithmetic, GPU sharing)
and section 2 "Neighbours, recommendations and why" (a "shares the section at 1:02" claim
needs timestamped representations and an alignment evaluation; the cap can omit later
sections; similarity is not recording identity).

Constraints:
- **Parity.** `analysis/audio-embeddings` requires production pooled vectors to match
  benchmark run `20261027-031711-c7c3698` at cosine >= 0.999. Storing windows must not change
  the pooled vector.
- **GPU.** The shared GTX 1070 runs `gpu` jobs serially; re-embedding 862 assets at the
  benchmarked ~77 audio-s/s is on the order of 30-40 minutes of model time in idealized
  arithmetic (862 x up to 180 s), not a measured end-to-end time.
- **Storage.** ~40 GB SSD budget (not measured free space). Raw window vectors for 862 assets
  are about 30 MiB; Postgres overhead and backups are unmeasured.

## Goals / Non-Goals

**Goals:**
- Keep exactly the windows that produced each pooled vector, with timestamps.
- Make window coverage (and its truncation) explicit to any consumer.
- Measure whether window matching can localize sections before anything claims it can.

**Non-Goals:**
- Changing `PIPELINE`, window length, overlap or cap.
- Section-level UI, structure detection or cross-model window comparison.

## Decisions

### Decision 1: A sibling `audio_embedding_windows` table, same pipeline string

`audio_embedding_windows(asset_id -> audio_assets CASCADE, model, revision, pipeline,
window_index, start_s, end_s, is_tail, embedding vector, dim, job_id, created_at)`, primary
key `(asset_id, model, revision, pipeline, window_index)`, dimension check like
`audio_embeddings`. Vectors are stored exactly as the model returned them (not normalized),
so `pool(windows)` reproduces the stored pooled vector. The pipeline string stays
`w10-t3-cap180-fp32-mean-l2-v1` because the computation is unchanged; window presence is a
separate currency condition.

Alternatives: an array-of-vectors column on `audio_embeddings` (rejected: no per-window
query or index, and a 9 KiB+ TOASTed value per row on every pooled read); a Parquet sidecar
on HDD (rejected: a second store outside Postgres, ADR 0002/0005; no transactional link with
the pooled row); bumping `PIPELINE` to force a re-embed (rejected: it would mark parity
evidence stale for an unchanged computation).

### Decision 2: Write windows and pooled vector in one transaction

The job already holds the window array before pooling (`jobs.py` calls
`audio.pool(adapter.embed_windows(...))`). It keeps the array, writes window rows and the
pooled row together, and deletes rows of older revisions for that asset and model in the same
transaction. Timestamps derive from the window index, `WINDOW_S` and the tail length, so
they cannot drift from the cut.

### Decision 3: Currency includes windows (MODIFIED requirement)

`is_current` additionally requires a window set for the same revision and pipeline. The 862
production assets therefore count as missing once and are re-embedded by the operator's
normal `embed` command; nothing is scheduled. The GPU parity test is extended to check
`pool(stored windows) == stored pooled`.

Alternative: a separate `embed-windows` backfill that recomputes windows without touching
pooled rows. Rejected: two code paths that could disagree; the parity test would need to
cover both.

### Decision 4: Exact window matching, internal only

`window_matches(asset_a, asset_b, model, k)` loads both assets' windows (at most 18 each),
computes the 18 x 18 cosine matrix in Python and returns the top `k` pairs. No pgvector ANN
index: library-wide window search (about 15,500 rows) is an exact scan when it is needed
later. The operation is exported for analysis and audio-lab use and is not registered on
any router.

### Decision 5: Alignment evaluation in audio-lab

`audio-lab align` exports window vectors from an embed run (audio-lab writes them to its
run Parquet as well), pairs each Deezer preview with its full track, and establishes a
reference offset by cross-correlating the decoded preview against the full track's
waveform (or a Chromaprint offset), accepting only offsets with a clear correlation peak.
It reports the share whose best window match lies within 10 s of the reference offset,
with n and "offset unavailable" counts, plus the share of previews whose excerpt lies
beyond the 180 s cap (unlocatable by design). A second step samples cross-track
top-window pairs for blind owner judgment ("these sections sound alike": yes/no/unsure).

Alternative: owner judgments only. Rejected: preview localization gives an objective,
cheap first check; owner judgments test the actual product claim.

## Risks / Trade-offs

- [10 s non-overlapping windows are too coarse to align sections] -> the evaluation reports
  it; a later pipeline change can try overlap or beat-synchronous windows.
- [Previews beyond 180 s cannot be located] -> counted separately, and it is the cap
  disclosure in action.
- [Re-embed contends for the shared GPU] -> operator-started, serial queue; run when no
  other GPU workload is active.
- [Storage grows with longer caps later] -> measured size recorded now (task 4.2) to project
  future pipelines against the SSD budget.
- [Someone exposes window matches as a "why"] -> the HTTP route-table test fails, and the
  spec requires a cited evaluation first.

## Migration Plan

Additive migration; deploy the GPU worker, then the operator runs `embed`. Rollback:
revert currency logic (windows become optional) and drop the table; pooled vectors are
untouched throughout.

## Open Questions

- Whether a later pipeline version should lift the 180 s cap for windows only; decided
  after the alignment evaluation and a storage measurement.
