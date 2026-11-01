# Tasks

## 1. Guardrails

- [ ] 1.1 Add the `lyrics-caption` extra to `services/audio-lab/pyproject.toml` and lock it with uv; verify `services/audio-lab/tests/test_imports.py::test_lyrics_caption_extra_optional` passes with and without the extra installed
- [ ] 1.2 Implement local-only enforcement (no endpoint settings, refusal of remote-API env vars, offline after `download`) and the in-repo output refusal; verify `services/audio-lab/tests/test_lyrics_caption_guards.py::test_remote_endpoint_refused`, `::test_inference_no_network` (sockets blocked) and `::test_output_inside_repo_refused` pass
- [ ] 1.3 Add license and code records for Whisper, Demucs, MusiLingo (MERT-330M, Vicuna), LLark, Audio Flamingo 3, Qwen2.5-Omni-3B, LyricWhiz and the pitch-correction method, from their repositories and model cards; verify `services/audio-lab/tests/test_lyrics_caption_guards.py::test_unreviewed_remote_code_refused` and `::test_noncommercial_marked` pass

## 2. Commands

- [ ] 2.1 Implement `audio-lab lyrics` (Jam-ALT normalization, WER/CER per language with n, Demucs on/off, gap hallucination count, Jam-ALT caveats in the report); verify `services/audio-lab/tests/test_lyrics.py` passes on a synthetic two-song fixture with a known gap
- [ ] 2.2 Implement `audio-lab captions` (Song Describer subset, MuChoMusic accuracy with answered/failed/skipped counts, YouTube-only items skipped); verify `services/audio-lab/tests/test_captions.py` passes with a stub model under `tests/`
- [ ] 2.3 Implement the precision ladder and cost recording (precision, load time, s per audio minute, peak VRAM, GPU name; out-of-memory as `unavailable`); verify `services/audio-lab/tests/test_lyrics_caption_cost.py::test_oom_is_unavailable` and `::test_cost_fields_recorded` pass
- [ ] 2.4 Implement the pitch-correction run with tentative wording; verify `services/audio-lab/tests/test_pitch_correction.py::test_report_wording` passes, or the method is recorded `unavailable` with `::test_unavailable_method_reported`
- [ ] 2.5 Add an import-linter contract forbidding imports of audio-lab lyric and caption code from `sidetrack` and `services/api`; verify `lint-imports` passes

## 3. Rack runs

- [ ] 3.1 Run every candidate's precision ladder on the GTX 1070 and record which load, at what precision and peak VRAM, in docs/AUDIO-BENCHMARK.md; verify the run ID in the doc exists
- [ ] 3.2 Run `audio-lab lyrics` on Jam-ALT and `audio-lab captions` on Song Describer and MuChoMusic; record aggregate metrics with n, cost and the owner's decision on whether any direction merits a production proposal in docs/AUDIO-BENCHMARK.md; verify the run IDs in the doc exist and no transcript text is committed (`git grep` of the run's sample lines returns nothing)

## 4. Records

- [ ] 4.1 Update docs/status.yaml with an exploratory lyrics/captioning entry (audio-lab only, not in production, run IDs as evidence); run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint`, `make test.unit` and `lint-imports`. No ADR is needed because no model is accepted for production.

## Workflow follow-up

- Archive once every scenario has a passing test.
- Any production use (lyric themes, captions, a pitch-correction facet) needs a new change, an ADR and rights review for lyrics.
