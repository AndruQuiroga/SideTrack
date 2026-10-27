# Design

## Context

See proposal.md (Why, Impact) for motivation and the observed state.

- **Hardware.** The rack's card is a GTX 1070 (observed 2026-10-27; long documented as a
  1070 Ti): Pascal, compute capability 6.1, 8 GB, and fp32 only in practice. It has about
  20% fewer CUDA cores than a Ti.
  - **Where it is:** in Proxmox host stache-0, and not yet passed through to docker-0
    (VM 100, Ubuntu 26.04, a Linux Swarm manager). Passthrough, the driver and the container
    toolkit are stache-infra work, done before group 3.
  - The benchmark ran on Windows with an RTX 5070.
- **Benchmark numbers.** On the RTX 5070 (run `20261027-031711-c7c3698`, about 70,600 s
  of audio per model), MuQ-MuLan embedded 163 audio-seconds per second and peaked at
  2,859 MiB; MuQ did 172 audio-seconds per second and peaked at 4,693 MiB.
- **How embedding runs.** `embed_run` loads one model at a time, embeds every asset, then
  unloads. Each asset's windows (at most 18 for a 180 s full track) go through one forward
  pass, grouped by length.
- **Consumer.** `add-muq-mulan-embeddings` needs four things from this change: the torch
  build, proof that a Swarm service can use the GPU, the batch size and job time limit, and
  confidence that cross-GPU fp32 vectors agree to 0.999.

## Goals / Non-Goals

**Goals:**
- Run the benchmark's exact model code and versions on the 1070 Ti, with only the CUDA
  runtime changed.
- Produce numbers that size the production job, and a parity figure that tests the
  integration's 0.999 threshold before it is relied on.

**Non-Goals:**
- A production image or service, and tuning for speed (batching across assets, fp16,
  `torch.compile`).

## Decisions

### Decision 1: torch 2.11.0 from the CUDA 12.6 index

PyTorch still publishes `torch-2.11.0+cu126` and `torchaudio-2.11.0+cu126` for cp311 on
Linux x86_64. That's the same torch and torchaudio version as the benchmark, so the only
difference is the CUDA runtime (12.6 instead of 12.8). It also keeps `muq==0.1.0` and
`transformers==4.57.6` unchanged.

The built image's cu126 torch reports `sm_50` through `sm_90`, including `sm_60`, whose
binaries run on 6.1. torch's own compatibility table says the 6.0 build supports 6.0–6.9
except 6.2. It still has to be confirmed on the card (task 3.2). If it doesn't, the fallback is the newest torch
release with Pascal kernels and a matching torchaudio. That changes this design's pins, not
its approach, and the deviation is recorded with the run.

Alternative: an older torch on CUDA 11.8. Rejected unless needed: it adds version drift
against the benchmark for no gain.

### Decision 2: A conflicting `models-pascal` extra in the same audio-lab lock

The new extra in `services/audio-lab/pyproject.toml` lists the same packages as `models`.
uv routes torch and torchaudio to `pytorch-cu126` for `models-pascal` and to
`pytorch-cu128` for `models` (per-extra `[tool.uv.sources]`), and
`[tool.uv] conflicts = [[{ extra = "models" }, { extra = "models-pascal" }]]` stops both
being installed at once. One lock keeps every other pin identical between the two GPUs.

`models-pascal` also pins `torchvision==0.26.0` from the cu126 index; `models` doesn't.
torchvision arrives transitively through muq's `x-clip`, and uv applies index sources only
to direct dependencies. PyPI's Linux torchvision wheel is built against PyPI's torch, so with
the cu126 build its compiled ops don't register, and both models fail to load with
`operator torchvision::nms does not exist`. That happened on the first docker-0 warm-up on
2026-10-27. On Windows, PyPI ships a `+cpu` torchvision that loads with any torch, which is
why the RTX 5070 benchmark never hit this. The image now calls `torch.ops.torchvision.nms` at
build time, so a mismatch fails the build.

Alternative: a second audio-lab project directory. Rejected: duplicated configuration and
two locks that drift apart.

### Decision 3: A local audio-lab image, run with `docker run --gpus all`

`services/audio-lab/Dockerfile` uses `python:3.11-slim`, ffmpeg and uv, then runs
`uv sync --frozen --extra models-pascal` and uses `audio-lab` as the entrypoint. The
operator builds it on docker-0; it isn't pushed to GHCR because it's a benchmark tool, not
a deployable service.

- **Size:** the image is about 11.7 GB, 7 GB of it torch and CUDA. uv's download cache
  lives in a build-cache mount, not in the image; inside the image it doubled the size to
  22.5 GB.
- **On docker-0:** with 56 GB free on its root disk, it fits. It's removed after the run.
- **Commit:** the image has no `.git`, so the build bakes the commit in as
  `AUDIO_LAB_COMMIT` for the run ID and `run.json`.

The run uses plain `docker run --gpus all` (not Swarm) with these mounts:
- the audio sample, read-only
- the manifest
- a run root
- a Hugging Face cache, so the weights download once

All of them sit under a staging directory on docker-0's root disk. The HDD isn't attached
to the VM, and the v2 audio is only 1.41 GiB.

The run directory is then copied back to `E:/sidetrack/benchmark` next to the RTX 5070 runs.
Benchmark data stays out of the repo.

### Decision 4: GPU access is stache-infra's job; this change only uses it

Passing the GPU through to VM 100 means:
- binding it to vfio-pci on stache-0
- adding a `hostpci` entry and restarting the VM
- installing a Pascal-capable NVIDIA driver (the 580 branch or older) in the guest
- installing the container toolkit
- making the GPU visible to Swarm services

These are rack changes with outages: docker-0 is a Swarm manager carrying ingress and
proxy. They're done and recorded in stache-infra under its change rules, in their own
session, and the owner approves every reboot.

Swarm services don't accept `--gpus`. The preferred method is `nvidia` as docker-0's
default runtime, with `NVIDIA_VISIBLE_DEVICES=all` set on the service. The fallback is
node generic resources.

This change only depends on the outcome:
- **3.1:** `nvidia-smi` works on the host and in a container.
- **3.2:** the torch check passes in the audio-lab image.
- **3.3:** a throwaway Swarm service sees the GPU. `deploy/README.md` records the method so
  `gpu-worker` can use it.

### Decision 5: Time the full v2 manifest for both models

The run embeds all 704 assets of the v2 manifest (about 70,600 s of audio per model) with
`muq-mulan` and `muq`, as on the RTX 5070. That gives:
- throughput comparable figure for figure with the 5070 run
- peak memory against the 8 GB card
- parity across every asset (Decision 6)

At an assumed 3–5 times slower than the 5070, that's roughly 25 to 40 minutes per model.
The audio files the manifest references (1.41 GiB) are copied to the staging directory on
docker-0's root disk at the same relative paths. They are the owner's own files, so ADR 0007 is unchanged: nothing fetches or serves
audio.

### Decision 6: Parity as a within-model, cross-run command

`audio-lab parity` joins two runs' `embeddings.parquet` on SHA-256 for one model. It checks
from both `run.json` files that the model's revision and window settings match, then reports
cosine statistics. Comparing one model's vectors across hardware is consistent with ADR
0004, which forbids comparing different models.

**Target:** median ≥ 0.9999 and minimum ≥ 0.999 for both models. If the minimum misses, the
outliers are inspected (decode differences between ffmpeg builds are the likeliest cause).
`add-muq-mulan-embeddings`'s 0.999 parity threshold is then revisited with that evidence
before it is applied.

### Decision 7: How the run sizes the production job

The figures go into the integration's Decision 5 (its task 1.2), derived as:
- **Per-batch time:** load seconds plus batch size × 180 s ÷ 1070 Ti throughput, the
  worst case of full tracks at the cap.
- **Time limit:** the batch size is set so that per-batch time is at most half the time
  limit. The time limit stays at 1,800 s unless the run shows a reason to change it.
- **MuQ's cost:** recorded as extra minutes per 1,000 assets. That's evidence for a later
  decision, not one made here.

### Decision 8: Load time is timed separately and the load probe is guarded

`embed_run` times `adapter.load` separately into `load_seconds`, and `wall_seconds` stays
the embedding loop only, so earlier runs stay comparable. `TorchAdapter.load` moves the
probe embedding inside its `try` and runs the architecture check from `_prepare`.
`environment()` adds `compute_capability` and `arch_list`. Unit tests cover the check with
a stubbed torch module; GPU tests cover the rest.

## Risks / Trade-offs

- [The cu126 2.11 build has no sm_61 kernels] → The compatibility check reports it clearly.
  Fall back to an older torch (Decision 1) and record the drift.
- [Pascal can't fit MuQ in 8 GB with 18 windows per forward pass] → The run records an
  out-of-memory error as the model being unavailable, through the guarded probe and
  per-asset failures. If it happens, a window-batch cap per forward pass is a small,
  separate follow-up, and MuQ-MuLan (2.9 GB on the 5070) remains the one that matters.
- [Different ffmpeg builds decode slightly differently between Windows and Linux] →
  Parity shows it. The production worker uses the Linux image's ffmpeg, so the 1070 Ti
  numbers are the relevant ones.
- [GPU passthrough or the Pascal driver fails on Proxmox 9.2 / Ubuntu 26.04] → It's found
  in the stache-infra session before this change touches the rack. Group 3 waits; groups 1
  and 2 stand on their own.
- [The GTX 1070 is slower than the 1070 Ti the estimates assumed] → Timing is measured,
  not estimated, and the derived batch size follows the measured throughput.

## Migration Plan

Nothing deploys from this repo. The `models` extra and existing runs are untouched. The
image, staged audio and run root are removed from docker-0 once the run is copied back.
Rack changes (passthrough, driver, runtime) have their own rollback in stache-infra.
