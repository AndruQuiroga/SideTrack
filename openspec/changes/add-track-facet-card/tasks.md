# Tasks

## 1. License review

- [ ] 1.1 Write docs/AUDIO-FACETS.md with a license table for every candidate (Beat This!, librosa, pyloudnorm or ffmpeg ebur128, the in-repo DSP code, vocal-presence candidates, All-In-One + NATTEN, madmom, Essentia), giving code, weights/data and dependency licenses at a pinned revision, remote-code use and an accepted/rejected/pending verdict; verify by review that Essentia and madmom models stay pending or rejected unless the licensor's clarification is linked

## 2. Audio-lab facet benchmark

- [ ] 2.1 Add the facet adapter protocol with mandatory license declarations and the `audio-lab facets` command writing versioned runs; verify `services/audio-lab/tests/test_facets.py::test_run_rows_and_run_json`, `::test_missing_license_declaration_refused` and `::test_unavailable_method_reported` pass
- [ ] 2.2 Implement CPU adapters (loudness, centroid, band energy, novelty boundaries, chroma key baseline, librosa beats) and verify `services/audio-lab/tests/test_facet_signals.py` passes on synthetic signals: the -23 LUFS reference tone, low/high sines, the 70/140 BPM click track, white noise for weak tonality and the 62-second step for boundaries
- [ ] 2.3 Add Beat This! and any license-accepted vocal or structure adapters under the `models-pascal` extra; verify `services/audio-lab/tests/test_facets_gpu.py` (marked `gpu`) loads them on the rack's GTX 1070 or records them unavailable with a reason, and records peak VRAM
- [ ] 2.4 Add reference scoring (beat F-measure 70 ms, tempo accuracy with and without octave errors, key accuracy with related-key credit separate, boundary hit rate 0.5 s/3 s) and altered-speed copies; verify `services/audio-lab/tests/test_facet_scoring.py` passes on hand-built annotation fixtures
- [ ] 2.5 Annotate beats and boundaries for a stratified owner set (outside the repo, aggregates only) and run the benchmark on docker-0; record per-facet scores with n, cost, peak VRAM/RAM, unavailable methods and the owner's per-facet decision in docs/AUDIO-BENCHMARK.md; verify the run ID in the doc exists and its `run.json` lists every license declaration

## 3. Facet storage and computation

- [ ] 3.1 Add the `AudioFacet` model and next-numbered migration (unique asset/facet/method_version, value-only-when-available check, cascade); verify `services/api/tests/test_migrations.py` and `tests/test_audio_facets_store.py::test_duplicate_rejected`, `::test_value_requires_available`, `::test_cascade_on_asset_delete` pass on Postgres
- [ ] 3.2 Register `audio_facets` as analysis-owned in docs/MODULES.md; verify `tests/test_module_layout.py` and `lint-imports` pass
- [ ] 3.3 Add the enabled facet-method registry and per-facet value schemas, containing only methods accepted in 1.1 and 2.5; verify `tests/test_audio_facets_registry.py::test_not_enabled_rejected` and `::test_enabled_methods_have_accepted_license_rows` (parses docs/AUDIO-FACETS.md) pass
- [ ] 3.4 Port the accepted CPU methods into `sidetrack/analysis/facets/` with the separate channel-preserving decode and 600 s cap; verify `tests/test_audio_facets_methods.py` reproduces the synthetic-signal scenarios and `tests/test_audio_facets_parity.py` matches the benchmark run's outputs for its fixture files
- [ ] 3.5 Add accepted GPU methods to `services/gpu-worker` dependencies only; verify `services/gpu-worker/tests/test_facets_gpu.py` (marked `gpu`) and that the root `uv.lock` contains no torch
- [ ] 3.6 Add `analysis.compute_facets` jobs on each method's queue with per-asset failure reasons and revision-aware skipping, and the `python -m sidetrack.audio facets` command; verify `tests/test_audio_facets_job.py` covers backfill counts, pruned-file failure, unavailable libraries, version bump replacement and that no schedule queues facet jobs

## 4. Read models, API and page

- [ ] 4.1 Implement the facet read model with `not_computed`/`no_audio`/`ambiguous` states and per-user percentiles with reference count and `insufficient_sample`; verify `tests/test_audio_facets_read.py` covers the 82nd-percentile, 29-asset `insufficient_sample`, other-user, `night_autoplay`-excluded and preview-only scenarios
- [ ] 4.2 Add `GET /tracks/{id}/facets` with the personal-data policy and regenerate `packages/api-client`; verify `services/api/tests/test_track_facets_route.py` covers 404, provenance fields, no audio URL or path in any response, and that no job is queued by a request
- [ ] 4.3 Add the facet panel to `/tracks/{id}` in `apps/web` (create the page with only this panel if `add-listening-visuals` has not landed); verify `apps/web/app/tracks/track-facets.test.ts` renders every state distinctly (including `ambiguous` link), tempo alternatives, percentile wording with n, the forbidden-terms check and text-only state labels, and `apps/web/app/no-fake-data.test.ts` still passes
- [ ] 4.4 Run the CPU facet backfill on production, then measure the `audio_facets` table size and record it with per-state counts in docs/AUDIO-FACETS.md; verify the recorded counts match a direct SQL count

## 5. Records

- [ ] 5.1 Write an ADR accepting the enabled facet methods and their licenses (and the GPU method's environment), update docs/status.yaml with an "Audio facets" capability and evidence paths, run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint`, `make test.unit` and `uv run --frozen --extra api --extra dev lint-imports`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
- Propose rhythmic regularity, texture-change and stereo-width facets after this benchmark, each with its own definition and evaluation.
