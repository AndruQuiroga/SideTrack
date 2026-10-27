# Tasks

## 1. Pascal environment

- [x] 1.1 Add the `models-pascal` extra, the `pytorch-cu126` index, per-extra torch/torchaudio sources and the `models`/`models-pascal` conflict to `services/audio-lab/pyproject.toml`, and relock; verify `uv lock --check --project services/audio-lab` passes, the lock resolves `torch==2.11.0+cu126` only for `models-pascal`, and `uv sync --project services/audio-lab --extra models` still installs the cu128 build on the RTX 5070
- [x] 1.2 Add `services/audio-lab/Dockerfile` (python:3.11-slim, ffmpeg, `uv sync --frozen --extra models-pascal`, `audio-lab` entrypoint); verify `docker build` succeeds and `docker run --rm <image> --help` prints the CLI help
- [x] 1.3 Document the Pascal extra, the image and the docker-0 run command in `services/audio-lab/README.md`; verify the documented commands match the ones used in group 3

## 2. Compatibility check, load time and parity

- [x] 2.1 Check the GPU's compute capability against `torch.cuda.get_arch_list()` before loading, move the load probe inside the error handling, and record `compute_capability` and `arch_list` in `run.json`; verify unit tests with a stubbed torch for the missing-`sm_61` and probe-CUDA-error scenarios, and a GPU test asserting both fields are present
- [x] 2.2 Record `load_seconds` per model, separately from `wall_seconds`; verify a unit test with a test-double adapter shows load time recorded and excluded from wall time, and the GPU test asserts it is greater than zero
- [x] 2.3 Add `audio-lab parity RUN_A RUN_B --model M [--threshold 0.999]`; verify unit tests on two synthetic runs for the same-model statistics and listing below the threshold, the different-revision refusal and the missing-model refusal, and a parity run between run `20261027-031711-c7c3698` and itself reports a minimum of 1.0
- [x] 2.4 Run `uv run pytest` in `services/audio-lab` and `uv run --extra models pytest -m gpu` on the RTX 5070; verify both pass

## 3. docker-0

- [x] 3.1 Confirm the stache-infra GPU passthrough work is done and recorded there (GTX 1070 passed through to VM 100, Pascal-capable driver and container toolkit in docker-0); verify `nvidia-smi` on docker-0 and in a CUDA 12.6 base container with `--gpus all` both show the GTX 1070 and a driver supporting CUDA 12.6, and record the driver version and the stache-infra evidence page
- [x] 3.2 Build the audio-lab image on docker-0 and run `python -c "import torch; print(torch.cuda.get_device_capability(), torch.cuda.get_arch_list())"` in it with `--gpus all`; verify capability (6, 1) and `sm_60` or `sm_61` in the list, or apply Decision 1's fallback and record it in design.md
- [x] 3.3 Using the Swarm GPU method stache-infra set up (default `nvidia` runtime preferred), run a throwaway one-replica service pinned to docker-0 that runs the torch check from 3.2 in the audio-lab image, then remove it; verify the service logs show capability (6, 1) and `sm_60` or `sm_61`, and document the method for `gpu-worker` in `deploy/README.md`
- [x] 3.4 Copy the v2 manifest's audio files (1.41 GiB) and the manifest to a staging directory on docker-0's root disk at their relative paths; verify a checksum pass over every manifest row matches its SHA-256 and the root filesystem keeps at least 20 GB free

## 4. Timing run

- [x] 4.1 Run `audio-lab embed` with `--model muq-mulan --model muq` over the v2 manifest on docker-0 with `--max-duration 600`, as in the v2 run; verify `run.json` shows both models `ok` with capability 6.1, a peak memory under 8,192 MiB, load seconds, and failures limited to those of run `20261027-031711-c7c3698`
- [x] 4.2 Copy the run to `E:/sidetrack/benchmark` and run `audio-lab parity` for both models against run `20261027-031711-c7c3698`; verify the medians are at least 0.9999 and the minimums at least 0.999, or record the outliers and their cause
- [x] 4.3 Record the run in docs/AUDIO-BENCHMARK.md: environment, throughput, peak memory, load time and parity for both models against the RTX 5070, the batch size and time limit derived by Decision 7, and MuQ's extra minutes per 1,000 assets; replace the "a follow-up change" sentence with the run ID; correct "GTX 1070 Ti" to GTX 1070 in docs/AUDIO-BENCHMARK.md, `openspec/config.yaml` and ADR 0006 (with a dated note); remove the image, staged audio and run root from docker-0; verify the doc names the run ID and every figure matches `run.json`

## 5. Records

- [x] 5.1 Update the "Embedding models (any)" entry in `docs/status.yaml` with the 1070 Ti result and run ID, then run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the CI staleness check passes
- [x] 5.2 Write the run's torch pin, batch size and time limit into `add-muq-mulan-embeddings` (design.md Decision 5, tasks 1.2 and 5.1 inputs), plus the GTX 1070 correction and the docker-0 audio location (root disk unless stache-infra attaches the HDD), with `/opsx:update`; verify `pnpm exec openspec validate --all --strict` passes

## Workflow follow-up

- Archive this change once every scenario has a passing test and the run is recorded, then start `/opsx:apply add-muq-mulan-embeddings`.
