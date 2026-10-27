# Design

## Context

See proposal.md for motivation, and the `analysis/audio-benchmark` spec for required behaviour. Constraints:

- **ADR 0004:** a standalone CLI, Parquet output, four named models, each adapter declares its checkpoint, licence and sample rate, and embeddings from different models are never compared.
- **Hardware:** the first runs are on the owner's RTX 5070 (Blackwell, sm_120, 12 GB). Blackwell needs PyTorch built for CUDA 12.8 or later, and those builds dropped Pascal (sm_61). So one environment can't serve both this PC and the rack's GTX 1070 Ti. This change targets the 5070, and the 1070 Ti environment is a follow-up.
- **Dependency isolation:** the root `pyproject.toml` must stay light, and uv resolves all extras into one lock. The lab is therefore its own uv project, like `services/extraction` today, and not a workspace member.
- **Input:** the `analysis/audio-assets` manifest CSV (path, sha256, kind, source, source ID, duration, verification, track ID, artist, title). The lab never connects to Postgres.

## Goals / Non-Goals

**Goals:**
- One command to embed about 200 assets (100 seeds × full + preview) with four models on one GPU in well under an hour.
- Neighbour lists the owner can judge quickly, by listening.
- Results that can be compared over time: the run directory plus `run.json` reconstruct exactly what ran.

**Non-Goals:**
- Approximate-nearest-neighbour indexes. Exact cosine over a few hundred vectors per model is instant.
- Integration with pgvector, the `gpu` queue or the API. That waits until a model passes.

## Decisions

### 1. Project layout and installation

```
services/audio-lab/
  pyproject.toml   # core deps: numpy, pyarrow, soundfile, soxr; extra "models": torch, torchaudio, transformers, muq
  uv.lock
  src/audio_lab/
    cli.py         # embed | report | score
    manifest.py    # read + validate manifest
    audio.py       # decode, mono, resample (soxr), chunk
    adapters/      # base.py, muq.py, muq_mulan.py, mert.py, clap.py
    runs.py        # run dir, run.json, Parquet writing, perf capture
    neighbours.py  # cosine top-k per model, self-retrieval
    metrics.py     # same-artist rate, separation, overlap
    duels.py       # blind A/B duel generation
    report/        # template.html (inline CSS/JS), __init__.py renders it
    score.py
  tests/           # core tests with generated WAVs and a test-double adapter
```

PyTorch comes from the `pytorch-cu128` index via `[tool.uv.sources]`, so `uv sync --extra models` gets Blackwell wheels. The pins are torch and torchaudio 2.11.0+cu128. muq requires torchaudio, whose last release (2.11) pins torch 2.11, and newer torch builds moved to CUDA 13. transformers is pinned to 4.57.6, the last 4.x, because MERT's remote modelling code targets transformers 4. Decoding uses `soundfile`, which reads FLAC, WAV and OGG/Opus through libsndfile, with an `ffmpeg` subprocess as the fallback for m4a and webm from yt-dlp. Decoding is mono-mixed and resampled with `soxr` to each adapter's rate.

Alternative considered: keeping the `services/extraction` name. Rejected, because it's tied to a planned HTTP microservice, while the lab is a CLI that serves nothing. The AGENTS.md layout table already says "the audio lab replaces it".

### 2. Adapter contract

```python
class Adapter(Protocol):
    name: str; checkpoint: str; revision: str; license: str
    sample_rate: int; dim: int; pooling: str; dtype: str
    def load(self, device) -> None: ...            # raises ModelUnavailable(reason)
    def embed(self, wave: np.ndarray) -> np.ndarray # one vector per asset
```

- **Clip pooling:** audio is cut into non-overlapping windows (default 10 s; the last partial window is kept if it's at least 3 s). The track vector is the mean of the window vectors, L2-normalised. Previews give about three windows, and full tracks are capped at the first 180 s of windows to bound time; both values are recorded.
- **MuQ:** mean over time of the final hidden state.
- **MERT:** mean over time of the average of all hidden layers. This is the commonly reported best general-purpose choice, and it's recorded as the adapter's `pooling`.
- **MuQ-MuLan and CLAP:** their audio projection embedding.
- **Metadata:** `revision` is the Hugging Face commit hash resolved at load. The sample rate and dimension are read from the checkpoint's config and asserted.
- **dtype:** fp32 for every model. The 12 GB card has room (peak 4.7 GB for MuQ), and it avoids reduced-precision differences between models. It's recorded per run.

### 3. Run directory

`--out` root → `<root>/<YYYYMMDD-HHMMSS>-<short git sha>/`, which holds:
- `run.json`
- `embeddings.parquet` (columns: run_id, model, sha256, kind, dim, vector as list<float32>)
- `failures.csv`

Creation uses `mkdir(exist_ok=False)`. Performance figures:
- **peak VRAM:** `torch.cuda.max_memory_allocated`, reset per model
- **wall time:** `time.perf_counter` around each model's loop
- **audio seconds:** the sum of decoded durations actually embedded

### 4. Report

`audio-lab report RUN_DIR --manifest CSV --audio-dir PATH` renders one HTML file with all CSS and JS inline, plus `metrics.json`. The neighbour pool per model is all full-track assets. Previews act only as queries for self-retrieval.

**Duels (the main view).** The first version asked for good, bad or unsure per seed and model. On the owner's real library every list sounded reasonable, so that couldn't separate models that disagree on most neighbours. Duels replace it:
- **Pairing:** for each seed and each pair of models (A, B), walk both top-10 lists in rank order and take the first rank r where A[r] ≠ B[r]. The duel compares A[r] with B[r]. If the lists agree at every rank, there is no duel for that pair. Rank-matched picks keep the comparison fair: neither model's candidate comes from deeper in its list than the other's.
- **Order:** duels are generated in Python (`duels.py`) and embedded in the page. Their order is fixed by a `random.Random` seeded with the run ID. They're shuffled, then interleaved round-robin across pairs, so any prefix the owner judges covers every pair about equally. The left and right sides are also drawn from that generator. This only orders the page; it touches no embedding.
- **What the page shows:** the seed and two candidates, with artist and title but no model names. Each has a play button that seeks 35% into the track, using the manifest's duration, so a clip starts in the body of the song rather than the intro. Only one clip plays at a time.
- **Keys:**
  - Space plays the seed; Q and W play the candidates.
  - 1 or 2 picks the closer candidate; = says they're equally close.
  - Backspace undoes the last vote; S skips a duel.

  The page advances as soon as a vote is cast.
- **Blindness:** model names appear only on the results tab, which shows live standings. The duel view never names models.
- **Saving:** votes are kept in `localStorage` keyed by run ID and exported with "Download duels.json" as `{run_id, votes: [{seed, a, b, winner}]}`, where `winner` is a model name or `"tie"`.

**Browse view.** A read-only seed list with one column per model, showing its top 10 (artist – title, similarity, player).

**Metrics.** `metrics.py` computes the same-artist rate, separation and overlap described in the spec. Credited artists are split on `,`, `&`, `+`, `/`, `x`, `feat.` and `with`, the same rule acquisition uses. The rule is copied here because the lab never imports `sidetrack`.

File URLs work because the owner opens the report locally. Nothing is uploaded, and the audio stays on disk (ADR 0007).

Alternative considered: a small local web server. Rejected, because a static file is enough and keeps "never served over HTTP" simple.

### 5. Pass gate

The gate goes in `docs/AUDIO-BENCHMARK.md`, using the owner's judgement as ADR 0004 requires. A model is a candidate when:
- at least 40 duels are judged in one run
- it has the highest duel win rate, and that rate is at least 0.55
- its preview→full recall@10 is 0.8 or more

If the top two win rates are within 0.05, the owner chooses between them on cost and capability, such as MuQ-MuLan's text tower. The thresholds are a starting point, and the owner can revise them in that doc with a dated note. No model passes automatically. The doc records the owner's decision.

### 6. CI

A new `audio-lab` job runs `uv sync --project services/audio-lab` (core only, no torch) and `uv run --project services/audio-lab pytest`. The tests cover:
- manifest validation
- chunking and resampling with generated WAVs
- the run directory and `run.json` schema, through a test-double adapter under `tests/` that hashes input bytes into a vector
- the neighbour maths, self-retrieval, metrics, duel generation and score
- report rendering, checking for no external URLs
- the unavailable-model path when torch is absent

Real adapters are tested by a `gpu`-marked test that's skipped in CI. It embeds 2 generated clips per model and asserts the declared dimension and a finite, non-constant output.

## Risks / Trade-offs

- [MuQ-MuLan safetensors loading is reported broken] → Load the original `.bin` weights at a pinned revision, and record which in `run.json`.
- [CC BY-NC weights] → Personal and non-commercial use only. Recorded per adapter in `run.json` and in `docs/AUDIO-BENCHMARK.md`.
- [Windows quirks in Hugging Face cache symlinks and ffmpeg discovery] → Document `HF_HUB_DISABLE_SYMLINKS_WARNING` and the ffmpeg install in the README, and fail with a named missing tool.
- [The 5070 isn't production hardware] → The 1070 Ti run is required before integration, as a follow-up change with its own cu12.6 or older environment.
- [Deezer previews are 30 s of the song's middle] → Self-retrieval measures robustness to that. Neighbour judging uses full tracks only.

## Migration Plan

There's no database, image or deploy change. Removing `services/extraction` affects nothing that runs; it's built nowhere since `deploy-on-stache-rack` removed its compose profile.
