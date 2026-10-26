# Proposal

## Why

Audio-first listening intelligence is why Sidetrack was rebuilt, and no real audio model has ever run in it. Observed: `services/extraction` is an empty FastAPI app planned around openl3 and TensorFlow (`services/extraction/src/extraction/app.py`). `scripts/bench_extractor.py` "benchmarks" with `_simulate_work` and writes made-up timings to `bench_extractor_baseline.json`. ADR 0004 says to prove models on about 100 tracks with a standalone benchmark before building product on them. This change builds that audio lab, so the owner can decide which model, if any, Sidetrack should use.

## What Changes

- **Replace `services/extraction` with `services/audio-lab`**, a standalone Python project with its own `pyproject.toml` and `uv.lock`, so PyTorch never enters the root lock. It installs in two layers:
  - **core:** manifest reading, Parquet, neighbours and report. No PyTorch; CI tests this layer.
  - **`models` extra:** PyTorch for CUDA 12.8 (Blackwell), transformers and muq.
- **CLI `audio-lab embed`:** reads the manifest exported by `add-audio-acquisition`, runs one or more model adapters over every asset, and writes versioned results to a run directory:
  - `embeddings.parquet`: one row per asset per model
  - `run.json`: git commit, adapter checkpoints and licences, sample rates, dtype, GPU name, driver, CUDA and torch versions, manifest hash
  - per-model performance: seconds of audio per second, peak VRAM, failures
- **Four adapters per ADR 0004:** MuQ (`OpenMuQ/MuQ-large-msd-iter`), MuQ-MuLan (`OpenMuQ/MuQ-MuLan-large`), MERT (`m-a-p/MERT-v1-95M`) and CLAP (`laion/larger_clap_music`). Each declares its checkpoint and revision, licence, input sample rate, embedding dimension and pooling. A model that can't load reports itself unavailable. It never yields placeholder vectors.
- **CLI `audio-lab report`:** computes cosine nearest neighbours within each model only, never across models (ADR 0004). It writes a static HTML report: each seed with its top-10 neighbours per model side by side, local `<audio>` players for the owner's own files, and good/bad/unsure buttons. Verdicts are kept in the browser and exported as `verdicts.json`.
- **An objective check alongside the owner's judgement:** for seeds with both a full track and a Deezer preview, the report shows how often each model ranks the preview's own full track first, and within the top 10.
- **CLI `audio-lab score`:** reads `verdicts.json` and prints and stores each model's agreement rate. The ADR 0004 gate is recorded in `docs/AUDIO-BENCHMARK.md`.
- **Removed:** `services/extraction/`, `scripts/bench_extractor.py` and `scripts/bench_extractor_baseline.json`.

## Capabilities

### New Capabilities
- `analysis/audio-benchmark`: what the audio lab measures and records, how it compares models without mixing their embedding spaces, how it reports neighbours for human judgement, and its honesty guarantees.

### Modified Capabilities
None.

## Out of scope

- **Integration into Sidetrack:** pgvector columns, the `gpu` queue, API or web features. ADR 0004 defers these until a model passes.
- **Measuring the rack's GTX 1070 Ti.** PyTorch's CUDA 12.8+ builds, the only ones that support the owner's RTX 5070, dropped Pascal. A 1070 Ti run needs a second, older environment and is a follow-up change. ADR 0004's "measures the GTX 1070 Ti" stays a requirement for integration, not for this first benchmark.
- **Fine-tuning, training, or genre and mood classifiers.**
- **Text-to-music search with MuLan or CLAP text towers.** Audio embeddings only.

## Impact

- **New:** `services/audio-lab/` (source, tests, README, lock). The run output directory lives outside the repo (`--out`, HDD recommended).
- **CI:** a new job that installs the lab's core layer and runs its tests. No GPU and no model downloads.
- **Docs:**
  - AGENTS.md layout table and `docs/MODULES.md`: extraction → audio-lab
  - root `pyproject.toml` comment
  - `docs/status.yaml`: "Audio feature extraction" and "Embedding models (any)" rows
  - new `docs/AUDIO-BENCHMARK.md`
- **Depends on** `add-audio-acquisition` for real input. The lab's tests use generated sine and noise WAV files under `services/audio-lab/tests/`.
- **Licences:** MuQ, MuQ-MuLan and MERT weights are CC BY-NC 4.0, which is fine for this personal, non-commercial project. CLAP is Apache-2.0. Weights download to the Hugging Face cache, never into the repo.
