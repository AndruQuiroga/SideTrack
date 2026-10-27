# 0010: MuQ-MuLan audio embeddings in pgvector, on a separate GPU worker

- Status: accepted
- Date: 2026-10-27

## Context

ADR 0004 required a benchmark before any audio model reached Sidetrack. The v2 benchmark
(run `20261027-031711-c7c3698`, docs/AUDIO-BENCHMARK.md) passed the gate, and the owner
picked MuQ-MuLan as the lead model. Its joint audio–text space allows text queries later,
and it leads on genre. MuQ was kept as a second model for song recognition and artist
grouping. The rack's GPU is a GTX 1070 (Pascal). There, MuQ-MuLan runs at 77 audio-seconds
per second in 2.8 GB, and matches the benchmark's vectors to a cosine of at least 0.99999
(run `20261027-172855-0c32766-dirty`).

## Decision

- **Model:** MuQ-MuLan (`OpenMuQ/MuQ-MuLan-large` at `2e01c796`, 512 dimensions) is the only
  enabled embedding model. MuQ is added when a feature needs recognition or artist grouping.
- **Storage:** one analysis-owned `audio_embeddings` table holds one vector per asset and
  model, in an untyped pgvector column with a dimension check. Each row records the
  checkpoint revision and a preprocessing `pipeline` version. A new model needs no
  migration. Search is exact cosine within one model, revision and pipeline.
- **Execution:** `analysis.embed_audio` jobs of up to 128 assets run on the `gpu` queue,
  one at a time, with a 30-minute limit. The owner queues them with
  `python -m sidetrack.audio embed`; nothing schedules them.
- **Environment:** PyTorch lives only in `services/gpu-worker`, its own uv project and
  `sidetrack-gpu` image (torch 2.11 on CUDA 12.6, the newest build with Pascal kernels). The
  root lock, CI and the API image stay free of PyTorch, and the API never imports numpy or
  torch.
- **Deployment:** the `gpu-worker` service is pinned to docker-0 and gets the GPU through
  the nvidia default runtime (stache-infra). It reads audio read-only from
  `/srv/sidetrack/audio`.

## Consequences

- **Licence:** MuQ-MuLan's weights are CC BY-NC 4.0, so stored vectors are for this
  personal, non-commercial project only.
- **Drift:** production preprocessing is a copy of audio-lab's. A GPU parity test against
  the benchmark run guards it, and any change bumps `pipeline`, which marks old vectors stale.
- **Hardware:** docker-0's driver must stay on the 580 branch, the last that supports
  Pascal. Swarm doesn't reserve the GPU, so GPU services share its 8 GB.
- **Audio:** audio reaches docker-0 only by the owner copying it. Missing files are reported
  per asset, never faked.
