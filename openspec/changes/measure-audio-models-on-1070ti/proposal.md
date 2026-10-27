# Proposal

## Why

`add-muq-mulan-embeddings` puts MuQ-MuLan on the rack's GTX 1070 Ti (Pascal, sm_61, 8 GB),
but no audio model has run on that card yet. docs/AUDIO-BENCHMARK.md makes 1070 Ti timing a
condition of integration. The benchmark environment can't run there: its torch build comes
from the CUDA 12.8 index, which dropped Pascal. The integration's torch version, batch size
and job time limit all depend on numbers that don't exist yet.

## What Changes

- **Pascal environment for audio-lab.** A `models-pascal` extra pins the benchmark's own
  torch and torchaudio 2.11.0 from the CUDA 12.6 index, which still publishes them for
  Python 3.11 on Linux. It sits in the same lock as the existing `models` extra (CUDA 12.8),
  and the two can't be installed together.
- **audio-lab container.** A Linux image (Python 3.11, ffmpeg, the `models-pascal` extra)
  is built and run on docker-0 with the GPU, the audio sample and a run root mounted. It is
  a benchmark tool: not published and not in the stack.
- **GPU compatibility check.** Before a model loads, audio-lab checks that the torch build
  has kernels for the GPU's compute capability, and reports the model unavailable with both
  values if not. The load probe's CUDA errors are reported the same way instead of crashing
  the run. `run.json` records the compute capability and the build's architecture list.
- **Model load time.** Runs record how long each model took to load, separately from
  embedding time, because production jobs load the model once per batch.
- **Cross-hardware parity.** A new `audio-lab parity` command compares two runs' vectors
  for the same model, revision and SHA-256, and reports how closely they agree.
- **Swarm GPU check.** A throwaway one-replica Swarm service on docker-0 proves how a stack
  service gets the GPU. That's the method `gpu-worker` will use.
- **The timing run.** MuQ-MuLan and MuQ embed the full v2 manifest (run
  `20261027-031711-c7c3698`) on docker-0. Throughput, peak memory, load time and parity
  against the RTX 5070 run go into docs/AUDIO-BENCHMARK.md, with the batch size and time
  limit they imply for `analysis.embed_audio`.

Out of scope:
- The production `gpu-worker` environment, image and stack service
  (`add-muq-mulan-embeddings`).
- Whether MuQ is embedded in production. This run measures MuQ's cost, but the owner has
  decided that `add-muq-mulan-embeddings` stays MuQ-MuLan only.
- MERT and CLAP (dropped at the v1 gate), fp16 inference (Pascal's fp16 is slow and the
  benchmark is fp32), and any change to the pass gate.
- Changing the RTX 5070 `models` extra or re-running earlier benchmark runs.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `analysis/audio-benchmark`: runs check GPU compatibility before loading a model and
  record the result; runs record model load time; a parity command compares two runs of
  the same model.

## Impact

Current state:
- **Observed:** `services/audio-lab/pyproject.toml` pins `torch==2.11.0` and
  `torchaudio==2.11.0` to the `pytorch-cu128` index only. Its comment says that build has
  no Pascal support.
- **Observed:** `download.pytorch.org/whl/cu126` publishes `torch-2.11.0+cu126` and
  `torchaudio-2.11.0+cu126` for cp311 on manylinux x86_64 (checked 2026-10-26).
- **Observed:** the cu126 build's architecture list is `sm_50`, `sm_60`, `sm_70`, `sm_75`,
  `sm_80`, `sm_86`, `sm_90`, so `sm_60` binaries cover compute capability 6.1 (checked in
  the built image on 2026-10-27). Running on the card is still unverified.
- **Observed:** `TorchAdapter.load` (`adapters/torch_base.py`) runs its probe embedding
  outside the `try` that converts load errors to `ModelUnavailable`. A "no kernel image"
  CUDA error would end the run instead of marking the model unavailable.
- **Observed:** `embed_run` (`runs.py`) times only the embedding loop, so load time isn't
  recorded. `environment()` records the GPU name and driver but not the compute capability.
- **Observed (read-only inspection, 2026-10-27):** the rack's card is a **GTX 1070**
  (`10de:1b81`, GP104, 8 GB, sm_61), not the 1070 Ti the docs and the docker-0 node label
  name.
  - It sits on Proxmox host stache-0, bound to `nouveau`, and is **not passed through** to
    VM 100 (docker-0): there's no `hostpci` entry.
  - docker-0 has no NVIDIA driver and no container toolkit, and Docker's runtime is `runc` only.
  - The 3.6 TB HDD is unmounted on the host and not attached to the VM.
  - docker-0's 120 GB root disk has 56 GB free.
  - Details are in the shared notes and, once done, in stache-infra's evidence pages.
- **Observed:** no Swarm service uses a GPU yet (`deploy/stack.yml`).
- **Prerequisite outside this repo:** passthrough of the GPU to VM 100, plus the driver and
  container toolkit in the guest, is stache-infra work, done in its own session. Group 3
  starts once that work has verified that `nvidia-smi` works in a container on docker-0.
  The change keeps its name; the measured card is the GTX 1070.

Affected:
- `services/audio-lab`: `pyproject.toml`, `uv.lock`, a new `Dockerfile`, `adapters/torch_base.py`,
  `runs.py`, `cli.py`, a new parity module, tests, `README.md`.
- `docs/AUDIO-BENCHMARK.md` (the run) and `deploy/README.md` (how a service gets the GPU).
- docker-0: GPU passthrough, the driver, the container toolkit and any Docker runtime
  change, all made and documented through stache-infra, not this repo.
- Docs that call the card a 1070 Ti (`openspec/config.yaml`, ADR 0006,
  docs/AUDIO-BENCHMARK.md) are corrected with the recorded run (task 4.3).
- No change to the root package, root lock, API image or database.
