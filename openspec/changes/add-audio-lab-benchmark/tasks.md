# Tasks

## 1. Replace the stubs with the lab skeleton

- [x] 1.1 Delete `services/extraction/`, `scripts/bench_extractor.py` and `scripts/bench_extractor_baseline.json`. Create `services/audio-lab/` with `pyproject.toml` (core deps plus a `models` extra pinned to the cu128 index), `uv.lock`, a README covering Windows setup (ffmpeg, Hugging Face cache) and the `audio-lab` console script. Update the AGENTS.md layout table, the `docs/MODULES.md` line and the root `pyproject.toml` comment. Verify that `git grep -n "services/extraction\|bench_extractor"` returns only archived OpenSpec history, and that `uv sync --project services/audio-lab` succeeds.

## 2. Core pipeline (no PyTorch)

- [x] 2.1 Implement `manifest.py` and `audio.py` (decode, mono, soxr resample, 10 s windows with a 3 s minimum tail, 180 s cap). Prove them in `services/audio-lab/tests/test_audio.py` with generated sine and noise WAVs and a manifest row whose file is missing.
- [x] 2.2 Implement the adapter protocol, `ModelUnavailable` and `runs.py` (run directory, `run.json`, Parquet, failures, performance figures). Prove "Runs embed manifest assets with declared models", "Runs are versioned and reproducible" and the missing-file scenario in `tests/test_runs.py`, using a test-double adapter under `tests/`.
- [x] 2.3 Prove "Unavailable models are reported, never faked" in `tests/test_runs.py::test_real_adapters_without_torch_are_unavailable` by running real adapter names in an environment without torch. Add a static check that no adapter module calls a random or constant generator.

## 3. Neighbours, report and score

- [x] 3.1 Implement `neighbours.py`: cosine top-10 per model, exclusion of the seed's own assets, full-track pool, preview→full recall@1 and recall@10. Prove every scenario of "Neighbours are computed within one model" and "Self-retrieval is measured" in `tests/test_neighbours.py`.
- [x] 3.2 Implement the report template and render. Prove in `tests/test_report_and_score.py` that the HTML is self-contained (no `http(s)://` script or link), contains each seed and model column, and embeds the run ID. Check the verdict persistence and export scenario by hand in a browser, and describe the steps in the README.
- [x] 3.3 Implement `score.py`. Prove both scenarios of "Scoring summarises agreement per model" in `tests/test_report_and_score.py`.

## 4. Real models

- [x] 4.1 Implement the MuQ, MuQ-MuLan, MERT-v1-95M and CLAP adapters with pinned revisions. Each reads its sample rate and dimension from the checkpoint config and records its licence. Prove them with `tests/test_adapters_gpu.py` (marked `gpu`, run on the owner's PC): declared dimension, finite and non-constant output, and peak VRAM above zero.
- [ ] 4.2 Add the `audio-lab` CI job (core install plus pytest, no GPU), and verify it passes on the PR.

## 5. First benchmark and docs

- [x] 5.1 Write `docs/AUDIO-BENCHMARK.md`: how to run embed, report and score, the pass gate (at least 20 judged seeds including obscure picks, agreement of 0.70 or more, recall@10 of 0.8 or more, owner's decision), licences, and the 1070 Ti follow-up. Update the `docs/status.yaml` rows "Audio feature extraction" and "Embedding models (any)" to **partial**, with the lab tests as evidence, and regenerate `docs/STATUS.md`.
- [ ] 5.2 Owner run: embed the acquired ~100-seed manifest with all four models on the RTX 5070, open the report, judge at least 20 seeds, and score. Record the run ID, performance table, recall figures and agreement per model in `docs/AUDIO-BENCHMARK.md`, with the owner's pass or fail decision.
- [x] 5.3 Run the checks: lab pytest (core), the root `make lint` and unit selection (unchanged), and `pnpm exec openspec validate add-audio-lab-benchmark --strict`.

## Workflow follow-up

- If a model passes, propose the 1070 Ti environment and timing run, then the `analysis` integration (pgvector, `gpu` queue) as separate changes.
- Archive this change after 5.2 is recorded.
