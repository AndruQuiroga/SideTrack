# Proposal

## Why

Sidetrack can say two tracks are close in MuQ-MuLan space, but not where or why. The
embedding job already computes one vector per 10-second window and then throws them away
after mean pooling. Keeping those window vectors with their timestamps is the cheapest
foundation for section-level comparisons ("this part of A resembles that part of B"),
preview-in-full localization and later structure work, without another GPU pass per asset
beyond one re-embed. No section-level claim may be shown until an alignment evaluation
supports it (docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md, "Neighbours, recommendations
and why").

## What Changes

- **Window vectors stored with timestamps.** For each embedded asset, the GPU job also
  writes every window vector it pooled: window index, start and end seconds, whether it is
  the short tail, model, checkpoint revision and pipeline. Window and pooled vectors are
  written together, so the pooled vector always equals the normalized mean of its windows.
- **The 180-second cap is disclosed, not changed.** Windows cover exactly what the pooled
  vector covers; each asset records the analyzed span and its full duration, so nothing
  claims a later section was analyzed.
- **Re-embedding to populate windows.** An asset counts as current only when its pooled
  vector and its window set are both current, so the operator's next `embed` run re-embeds
  the 862 production assets once.
- **Retention and revisioning.** Windows follow their asset's lifetime and are replaced
  together with the pooled vector on a revision or pipeline change; no old-revision windows
  are kept.
- **An internal window-match read model**, marked experimental, that returns the best
  window pairs between two assets with their timestamps and similarity. It is not exposed
  over HTTP.
- **An alignment evaluation in audio-lab** before any user-facing section claim: locate
  each preview inside its full track and score the located offset against a reference
  offset, then an owner-judged set of cross-track window pairs. The result and the owner's
  decision gate any later "shares the section at 1:02" feature.

Out of scope:
- Any HTTP route, page or bot text that names a shared section or timestamp.
- Changing the window length, overlap, 180-second cap or pooling; that is a new pipeline
  version in its own change, because it invalidates the parity guarantee.
- Structure labels, beat-synchronous windows or facet computation (`add-track-facet-card`).
- A pgvector ANN index on windows; exact scans are enough at this scale.
- Window vectors for MuQ or any model other than the enabled one.

## Capabilities

### New Capabilities
- `analysis/audio-windows`: storage, provenance, coverage and lifetime of timestamped window
  vectors, the experimental window-match read model, and the gate on section-level claims.

### Modified Capabilities
- `analysis/audio-embeddings`: "Embedding is idempotent and revision-aware" now treats an
  asset as current only when its window set is also current, so existing assets are
  re-embedded once.

## Impact

Current state:
- **Observed:** the job decodes mono audio, cuts non-overlapping 10 s windows keeping a final
  tail of at least 3 s (or one short window for files under 3 s), caps full tracks at 180 s,
  embeds the windows and stores only `pool()` of them: mean then L2 normalization
  (`sidetrack/analysis/embeddings/audio.py`, `jobs.py`, `registry.py` `PIPELINE =
  "w10-t3-cap180-fp32-mean-l2-v1"`).
- **Observed:** `audio_embeddings` holds one row per asset and model in an untyped pgvector
  column with a dimension check (`sidetrack/analysis/models.py`, ADR 0010); production has
  862 MuQ-MuLan rows and no HTTP route uses them (docs/STATUS.md).
- **Observed:** MuQ-MuLan ran at about 77 audio-s/s with 2.8 GB peak VRAM on the GTX 1070
  (docs/AUDIO-BENCHMARK.md); the GPU is shared and not reserved by Swarm (ADR 0010).
- **Assumed:** at most 18 windows per full asset; 862 x 18 x 512 float32 is about 30 MiB of
  raw numbers. Row, TOAST and index overhead and backups add to that; task 4.2 measures it.
- **Assumed:** Deezer previews are 30-second excerpts from inside the full recording, so
  locating them inside the full track is a usable alignment test; task 3.2 checks how many
  reference offsets can be established.

Affected:
- `sidetrack/analysis/embeddings/` (jobs, store, new windows read model), `migrations/`
  (next free number), `services/gpu-worker/tests/test_parity.py`.
- `services/audio-lab` (window export in runs, `align` evaluation).
- Docs: docs/AUDIO.md (re-embed, storage), docs/AUDIO-BENCHMARK.md (alignment result),
  docs/MODULES.md, docs/status.yaml.

Dependencies: none required. `add-track-facet-card` and a future "why" feature consume it.
