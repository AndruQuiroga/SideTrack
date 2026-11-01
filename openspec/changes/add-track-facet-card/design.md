# Design

## Context

See proposal.md (Why, Impact). The evidence and cautions behind this design are in
docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md: section 2 "Interpretable audio facets" (method
limits, half/double tempo, atonal key, listener-relative percentiles, no gender, candidate
boundaries rather than drops), the model table (Beat This!, madmom, Essentia, All-In-One
licenses and dependencies) and section 3 "A practical validation protocol".

Constraints that shape the approach:
- **Hardware.** docker-0's GTX 1070 (8 GB, Pascal sm_61, fp32 in practice, CUDA 12.6 torch)
  is shared and not reserved by Swarm; MuQ-MuLan peaks at 2.8 GB. The VM had 24 GiB RAM
  shared with Minecraft containers limited to 15 GiB in October 2026 (a dated observation,
  not current capacity). Facet work must not assume it can sit beside other GPU jobs.
- **Environments.** PyTorch stays out of the root lock (ADR 0004, ADR 0010): neural methods
  live in audio-lab for benchmarking and in `services/gpu-worker` for production.
- **Storage.** ~40 GB SSD budget for Sidetrack's data (a budget, not measured free space);
  audio files on HDD.
- **Licenses.** Essentia is AGPLv3 and its models page and license file conflict
  (NC-SA vs NoDerivatives); madmom code is BSD but its models are CC BY-NC-SA; Beat This! is
  MIT; All-In-One needs NATTEN on Linux and has no drop class. Each must be reviewed at the
  exact pinned revision.

## Goals / Non-Goals

**Goals:**
- Measure candidate methods on the owner's library and the rack before any production code.
- One facet storage shape that can hold every facet, its provenance and its state.
- Read-time, per-user percentiles with an explicit reference count.

**Non-Goals:**
- Choosing a single "best" method per facet in this design; the benchmark decides.
- Facets for tracks (rather than assets); a track reads its preferred asset via
  `resolve-listens-to-audio`.

## Decisions

### Decision 1: Benchmark in audio-lab, then enable per facet

`audio-lab facets` adds facet adapters next to the embedding adapters, writes versioned runs
(Parquet + `run.json`) and a report section per facet. Candidates, subject to license review:

| Facet | Candidates to benchmark |
| --- | --- |
| Tempo/beats | Beat This! (MIT); librosa beat tracker (ISC) as a CPU baseline; madmom only if its model license is accepted |
| Key/mode | a librosa chroma + key-profile baseline written in-repo; Essentia KeyExtractor only after licensor clarification and an AGPL decision |
| Loudness | ffmpeg `ebur128` filter or pyloudnorm (MIT), checked against EBU Tech 3341/3342 test signals |
| Brightness, band energy | in-repo numpy/scipy STFT code (no model) |
| Vocal presence | candidates whose weights pass review; Demucs vocal-stem energy as a fallback measure |
| Structure | spectral novelty (in-repo, CPU) baseline; All-In-One only if NATTEN builds for sm_61 and licenses pass |

Each facet is enabled independently once it has a run, an accepted license row in
docs/AUDIO-FACETS.md and the owner's decision recorded in docs/AUDIO-BENCHMARK.md.

Alternative: integrate the first method that "works" directly in production. Rejected: ADR
0004 requires a benchmark gate, and published accuracy does not transfer to this library.

### Decision 2: One `audio_facets` table, JSON values with a per-facet schema

`audio_facets(id, asset_id -> audio_assets CASCADE, facet, method, method_version, pipeline,
state, reason, value jsonb, analyzed_start_s, analyzed_end_s, asset_duration_s, capped,
job_id, computed_at)`, unique `(asset_id, facet, method_version)`, check that `value` is null
unless `state = 'available'`. Each facet has a typed Pydantic schema for `value` (tempo:
`bpm`, `alternatives`, `beats`, `ambiguity`; key: `tonic`, `mode`, `strength`; loudness:
`integrated_lufs`, `lra_lu`; ...), validated on write and read. Analysis-owned.

`not_computed` is not stored: it is the absence of a row, so a new facet needs no backfill
of placeholder rows.

Alternatives: one column per facet on a wide table (rejected: every new facet needs a
migration and nulls cannot say why), or reusing `track_features` (rejected: keyed by track,
Spotify-shaped, includes `danceability`, and has no provenance).

### Decision 3: Facet decoding is separate from the embedding pipeline

Facets decode the asset with its original channels at the method's sample rate, up to a
facet cap of 600 s by default (recorded per row), instead of reusing the mono, 180 s
embedding decode. Loudness needs channels; tempo, key and structure are more useful beyond
three minutes. The decode version is the row's `pipeline`.

Alternative: reuse the embedding decode for consistency with vectors. Rejected for loudness
(R 128 weights channels) and structure; may be revisited for a facet whose benchmark shows
no difference.

### Decision 4: Queue per method; CPU methods stay out of the GPU worker

Each enabled method declares `queue`: CPU methods (loudness, centroid, band energy,
novelty structure, key baseline) run as `analysis.compute_facets` jobs on the default queue
in the main image with only lightweight extras; neural methods (Beat This!, a vocal model)
run on `gpu` in `services/gpu-worker`, one job at a time, never concurrently with an
embedding job (the GPU queue is serial). The command `python -m sidetrack.audio facets
[--facet ...]` queues batches, like `embed`.

Alternative: run everything on the GPU worker. Rejected: wastes the shared GPU and
couples simple DSP to the PyTorch image.

### Decision 5: Percentiles at read time over the requester's eligible library

The read model joins the requester's included plays (plays whose session `effective_kind`
is not `night_autoplay`) -> tracks -> preferred asset (`audio_for_track` from
`resolve-listens-to-audio`, status `ok` only; `ambiguous`, `no_audio` and `no_embedding`
tracks are excluded and counted) -> available facet rows of the same method version, and
ranks the target value among them: percentile = share of reference values strictly below
it. Below 30 reference assets the state is `insufficient_sample`, matching
`add-track-mood-scores`; 30 is a product threshold, not a statistical guarantee. Preview-only
assets are included and the response reports how many reference assets are previews.

Alternative: store percentiles per asset (rejected: shared assets have no single reference
population; notes section 6, item 3).

### Decision 6: API and page

`GET /tracks/{id}/facets` (analysis router, `listening:read`-style personal policy for the
percentile part, consistent with `identity/personal-data-visibility`) returns asset, link
method and facets. When `audio_for_track` reports `ambiguous`, the route returns that
state and no facets from any candidate asset until an operator confirms or rejects links.
The web track page renders a facet panel. If `add-listening-visuals`
has not created `/tracks/{id}`, this change creates the route with only the facet panel;
the visuals change adds its sections around it.

## Risks / Trade-offs

- [Beat This! or NATTEN fails on Pascal/cu126] -> CPU baseline or `unavailable`; the
  benchmark records the failure reason.
- [Licenses change or conflict] -> pin revisions, record license text hashes in the run,
  and keep Essentia/madmom models out until resolved.
- [Half/double-time and genre bias] -> always store alternatives; test on electronic and
  slowed edits; report per-genre scores where labels exist.
- [Reference annotations are scarce and rights-limited] -> owner-annotated beats/boundaries
  on a small stratified set; use Harmonix Set beat/section annotations only (not its
  spectrograms or YouTube audio); report n with every score.
- [GPU contention with embedding or Minecraft memory pressure] -> serial `gpu` queue,
  measure peak VRAM/RAM in the benchmark before enabling.
- [Users read percentiles as universal] -> wording names "your eligible library" and n.

## Migration Plan

New table only; no change to embeddings. Rollback: disable methods (empty enabled list) and
drop the table in a down-migration. Backfill is operator-started per facet.

## Open Questions

- Which vocal-presence candidate passes license review; if none, the facet ships later
  without changing the storage or API shape.
- The exact bass-band edges (for example 20-150 Hz) are fixed by the benchmark report and
  recorded in the method version.
