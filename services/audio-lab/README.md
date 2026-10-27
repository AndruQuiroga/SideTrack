# Sidetrack audio lab

A command-line benchmark for audio models (ADR 0004). It reads the manifest exported by
`python -m sidetrack.audio manifest`, embeds every asset with MuQ, MuQ-MuLan,
MERT-v1-95M and CLAP, and writes a versioned run you can judge in a local HTML report.
It serves nothing over HTTP and never touches Sidetrack's database.

This is its own uv project with its own `uv.lock`, so PyTorch never enters the root lock.

## Install

```bash
cd services/audio-lab
uv sync --python 3.11 --extra dev                 # core: tests, report, score (no PyTorch)
uv sync --python 3.11 --extra models --extra dev  # + PyTorch 2.11 (CUDA 12.8), transformers 4.57, muq
```

- **GPU:** the `models` extra targets CUDA 12.8 builds, which support Blackwell (RTX 50xx)
  but not Pascal (GTX 10xx). The rack's GTX 1070 Ti needs a separate environment; that's
  a follow-up change.
- **ffmpeg** must be on `PATH` for m4a and webm files from YouTube (`scoop install ffmpeg`).
- **Weights** download to the Hugging Face cache on first use: about 3 GB in total. On
  Windows, set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to silence the symlink notice. MERT runs
  remote code from its pinned Hugging Face revision (`trust_remote_code`).
- **Licences:** MuQ, MuQ-MuLan and MERT weights are CC BY-NC 4.0 (non-commercial; fine
  for this personal project). CLAP is Apache-2.0.

## Run

```bash
uv run --extra models audio-lab embed --manifest E:/sidetrack/manifest.csv \
    --audio-dir E:/sidetrack/audio --out E:/sidetrack/audio-lab-runs        # all four models
uv run --extra models audio-lab embed ... --model muq --model clap           # a subset
uv run audio-lab report E:/sidetrack/audio-lab-runs/<run-id> \
    --manifest E:/sidetrack/manifest.csv --audio-dir E:/sidetrack/audio
uv run audio-lab score E:/sidetrack/audio-lab-runs/<run-id> --votes duels.json
```

- **`embed`** creates `<out>/<YYYYMMDD-HHMMSS>-<git sha>/` containing `embeddings.parquet`,
  `failures.csv` and `run.json`. `run.json` records checkpoints, revisions, licences,
  sample rates, pooling, environment, and per-model throughput and peak VRAM. Assets are
  cut into 10 s windows; full tracks are capped at 180 s. A model that can't load is
  recorded as unavailable and never produces vectors.
- **`report`** writes `report.html` and `metrics.json` into the run. Open the HTML file
  locally. It has three tabs:
  - **Duels:** blind A/B duels. You see one seed and two candidates, each the pick of a
    different, hidden model at the same rank. Keys: `P` plays seed, A and B for 8 s each;
    `Space`, `Q` and `W` play one; `1` or `2` picks the closer one; `=` means equally close;
    `S` skips; `Backspace` undoes. Clips start 35% into the track. Votes are saved in the
    browser (per run ID); use **Download duels.json** to export them.
  - **Results:** live duel standings and the automatic metrics: preview→full recall,
    same-artist rate, separation, and top-10 overlap between models.
  - **Browse:** every seed's top 10 per model.
- **`score`** prints each model's wins, losses, ties and win rate (a tie counts as half a
  win), plus each pair's head-to-head, and writes `scores.json` into the run. It refuses
  votes from a different run or for models the run didn't embed.

The pass gate and recorded results are in `docs/AUDIO-BENCHMARK.md`.

## Test

```bash
uv run pytest                        # core, no GPU (also in CI)
uv run --extra models pytest -m gpu  # real models on a CUDA GPU
```

Checking the report by hand: open a run's `report.html`, answer a few duels, reload the
page (they persist), then export and confirm `duels.json` contains them with the run ID.
