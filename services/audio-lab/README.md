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
  but not Pascal (GTX 10xx). The `models-pascal` extra has the same pins from the CUDA
  12.6 index for the rack's GTX 1070; the two extras can't be installed together. Use
  it through the image below.
- **Compatibility check:** before a model loads on a GPU, `embed` checks that the torch
  build has kernels for the GPU's compute capability. If not, every model is recorded as
  unavailable with both values (for example `sm_61` against a CUDA 12.8 build).
- **ffmpeg** must be on `PATH` for m4a and webm files from YouTube (`scoop install ffmpeg`).
- **Weights** download to the Hugging Face cache on first use: about 3 GB in total. On
  Windows, set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to silence the symlink notice. MERT runs
  remote code from its pinned Hugging Face revision (`trust_remote_code`).
- **Licences:** MuQ, MuQ-MuLan and MERT weights are CC BY-NC 4.0 (non-commercial; fine
  for this personal project). CLAP is Apache-2.0.

## Seeds

```bash
uv run audio-lab seeds <extracted ListenBrainz export> --out E:/sidetrack/benchmark-v2
uv run audio-lab control-seeds --out E:/sidetrack/benchmark-v2
```

- **`seeds`** reads a ListenBrainz export and writes `seeds.csv`, `labels.csv`,
  `colisten.csv` and `seeds-report.json`. Everything it writes is personal data, so it
  refuses any `--out` inside the repo.
  - **Removes:** listens over 10 minutes, podcast titles (add your own with
    `--exclude-pattern`) and YouTube Labs entries.
  - **Credits channel uploads** titled "Artist - Title" to the real artist.
  - **Sleep tracks:** labels as `sleep` the tracks played mostly in night sessions (starting
    22:00–04:00, an hour or longer, 12 or more listens), and fills up to `--sleep-share` of
    the seeds with them.
  - **Picks** (`--count`, default 250, at most `--per-artist` per artist): songs you often
    play back to back first, then a balance across first-play years and play counts.
  - **Co-listening pairs:** two songs played back to back in at least `--min-sessions`
    separate daytime sessions.
- **`control-seeds`** writes `control-seeds.csv` and `control-labels.csv`: 10 tracks from
  each of 15 Deezer genre charts (`--genre` to change them), with at most one per artist.
- **Fetching:** both seed files are fetched with `python -m sidetrack.audio fetch --seeds …`.
  Concatenate `labels.csv` and `control-labels.csv` for the report.

## Run

```bash
uv run --extra models audio-lab embed --manifest E:/sidetrack/manifest.csv \
    --audio-dir E:/sidetrack/audio --out E:/sidetrack/audio-lab-runs        # all four models
uv run --extra models audio-lab embed ... --model muq --model clap           # a subset
uv run audio-lab report E:/sidetrack/audio-lab-runs/<run-id> \
    --manifest E:/sidetrack/manifest.csv --audio-dir E:/sidetrack/audio
uv run audio-lab score E:/sidetrack/audio-lab-runs/<run-id> --votes duels.json
uv run audio-lab parity E:/sidetrack/audio-lab-runs/<run-a> \
    E:/sidetrack/audio-lab-runs/<run-b> --model muq-mulan                    # one model, two runs
```

- **`embed`** creates `<out>/<YYYYMMDD-HHMMSS>-<git sha>/` containing `embeddings.parquet`,
  `failures.csv` and `run.json`. `run.json` records checkpoints, revisions, licences,
  sample rates, pooling, environment (including the GPU's compute capability and the torch
  build's architecture list), and per-model throughput, peak VRAM and model load time
  (`load_seconds`, not included in `wall_seconds`). Assets are
  cut into 10 s windows; full tracks are capped at 180 s. A model that can't load is
  recorded as unavailable and never produces vectors. With `--max-duration 600`, longer
  assets are skipped and recorded as `too_long`.
- **`report`** writes `report.html` and `metrics.json` into the run. Open the HTML file
  locally.
  - **Label files:** with `--labels` and `--colisten`, it adds genre precision@10 (control
    tracks only), the co-listening hit rate, and sleep purity with its base rate.
  - **Finalist duels:** `--duel-model muq --duel-model muq-mulan` limits the duels to those
    models. Metrics and the browse view still cover every model.

  The report has three tabs:
  - **Duels:** blind A/B duels. You see one seed and two candidates, each the pick of a
    different, hidden model at the same rank. Keys: `P` plays seed, A and B for 8 s each;
    `Space`, `Q` and `W` play one; `1` or `2` picks the closer one; `=` means equally close;
    `S` skips; `Backspace` undoes. Clips start 35% into the track. Votes are saved in the
    browser (per run ID); use **Download duels.json** to export them.
  - **Results:** live duel standings and the automatic metrics: preview→full recall,
    same-artist rate, separation, and top-10 overlap between models.
  - **Browse:** every seed's top 10 per model.
- **`parity`** compares one model's vectors in two runs (for example the same manifest on
  two GPUs) by asset SHA-256. It prints the shared asset count, the minimum, 1st-percentile
  and median cosine, and every asset below `--threshold` (default 0.999). It refuses runs
  with different checkpoint revisions or window settings for that model.
- **`score`** prints each model's wins, losses, ties and win rate (a tie counts as half a
  win), plus each pair's head-to-head, and writes `scores.json` into the run. It refuses
  votes from a different run or for models the run didn't embed.

The pass gate and recorded results are in `docs/AUDIO-BENCHMARK.md`.

## GTX 1070 (docker-0)

The rack's Pascal card runs audio-lab from a local image with the `models-pascal` extra.
The image is a benchmark tool: build it on docker-0, and don't push it or add it to the stack.

```bash
# On docker-0, in a copy of services/audio-lab (Dockerfile, pyproject.toml, uv.lock, src).
# There's no checkout there, so pass the commit it came from (add -dirty for local edits).
cd $STAGE/build
docker build --build-arg GIT_COMMIT=<short sha> -t audio-lab-pascal .
docker run --rm --gpus all --entrypoint python audio-lab-pascal \
    -c "import torch; print(torch.cuda.get_device_capability(), torch.cuda.get_arch_list())"

# STAGE=<staging directory on docker-0's root disk>; audio keeps the manifest's relative paths.
docker run --rm --gpus all --user $(id -u):$(id -g) \
    -v $STAGE/audio:/audio:ro \
    -v $STAGE/benchmark-v2:/benchmark:ro \
    -v $STAGE/audio-lab-runs:/runs \
    -v $STAGE/hf-cache:/hf \
    audio-lab-pascal embed --manifest /benchmark/manifest.csv --audio-dir /audio \
    --out /runs --model muq-mulan --model muq --max-duration 600
```

- **Commit:** the image has no `.git`, so `GIT_COMMIT` is baked in as `AUDIO_LAB_COMMIT`
  and goes into the run ID and `run.json`.
- **Weights** download once into the mounted Hugging Face cache. Run a one-asset `embed`
  first (to a throwaway `--out`), so the timed run's `load_seconds` doesn't include the
  download.
- **Long runs:** use `docker run -d --name …` and `docker wait`, so the run survives an SSH
  disconnect.
- **Afterwards,** copy the run directory back to `E:/sidetrack/audio-lab-runs` and compare
  it with the RTX 5070 run using `parity`.

## Test

```bash
uv run pytest                        # core, no GPU (also in CI)
uv run --extra models pytest -m gpu  # real models on a CUDA GPU
```

Checking the report by hand: open a run's `report.html`, answer a few duels, reload the
page (they persist), then export and confirm `duels.json` contains them with the run ID.

## Mood probes

`emotion-manifest` turns a local emotion dataset into a normal manifest plus `mood-labels.csv`,
so `embed` runs on it unchanged. `mood-probe` then fits linear valence and arousal probes on a
run, and writes `mood.json` with out-of-sample R², a mean-only baseline and paired comparisons.
The audio stays out of the repo, and only aggregate scores belong in the docs.

```bash
uv run audio-lab emotion-manifest --ratings E:/sidetrack/mood/deam/ratings.csv --audio-dir E:/sidetrack/mood/deam/audio --metadata E:/sidetrack/mood/deam/metadata.csv --out E:/sidetrack/mood/prepared
uv run --extra models audio-lab embed --manifest E:/sidetrack/mood/prepared/manifest.csv --audio-dir E:/sidetrack/mood/deam/audio --out E:/sidetrack/audio-lab-runs --model muq-mulan --model muq
uv run audio-lab mood-probe RUN --labels E:/sidetrack/mood/prepared/mood-labels.csv --predict-run LIBRARY_RUN --predict-out E:/sidetrack/mood/predictions.csv --predict-manifest MANIFEST
```

