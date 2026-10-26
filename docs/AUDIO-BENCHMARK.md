# Audio model benchmark

ADR 0004: prove audio models on real tracks before building anything on them. The
benchmark is `services/audio-lab` (see its README for commands). This page holds the
pass gate, the licences, and every recorded run.

## Models

| Name | Checkpoint (pinned revision) | Licence | Rate | Dim | Pooling |
| --- | --- | --- | --- | --- | --- |
| `muq` | `OpenMuQ/MuQ-large-msd-iter` @ `0562a578` | CC BY-NC 4.0 | 24 kHz | 1024 | mean over time, final hidden state |
| `muq-mulan` | `OpenMuQ/MuQ-MuLan-large` @ `2e01c796` | CC BY-NC 4.0 | 24 kHz | 512 | MuLan audio projection |
| `mert` | `m-a-p/MERT-v1-95M` @ `12af15fe` | CC BY-NC 4.0 | 24 kHz | 768 | mean over time of the layer average |
| `clap` | `laion/larger_clap_music` @ `a0b4534a` | Apache-2.0 | 48 kHz | 512 | CLAP audio projection |

- **Licences:** the CC BY-NC weights are non-commercial only. Sidetrack is a personal
  project, so that's acceptable, but it rules out any commercial use of these embeddings.
- **Embedding spaces:** different models' vectors are never compared with each other.
- **Inference:** fp32, with assets cut into 10 s windows and full tracks capped at 180 s.

## Pass gate

A model becomes a candidate for integration (pgvector, `gpu` queue) only when **all** of
these hold on one run:

1. **Judged seeds:** at least 20 seeds judged in the report, including the owner's obscure picks.
2. **Agreement:** good ÷ (good + bad) of at least **0.70** (`audio-lab score`).
3. **Self-retrieval:** preview→full recall@10 of at least **0.80** (from `retrieval.json`), where previews exist.
4. **Owner's decision:** recorded below with the run ID. Nothing passes automatically.

The thresholds are a starting point. Change them here with a dated note, never silently.

Integration also requires timing on the rack's GTX 1070 Ti. That needs a separate
PyTorch environment, because CUDA 12.8+ builds dropped Pascal. It's a follow-up change.

## Runs

### 2026-10-26: pipeline check on the 5-seed smoke manifest

Not a judgement run: five well-known seeds can't test obscure-track neighbours. It shows
that all four models load, embed the owner's real files (webm, m4a and mp3) and report
performance on the RTX 5070.

Run `20261026-203326-5a44f09`: 5 seeds × (full + preview) = 10 assets, 995 s of audio per
model. Environment: RTX 5070 (driver 617.14), torch 2.11.0+cu128, CUDA 12.8, Python 3.11.7,
Windows 10.

| Model | Embedded | Failed | Wall s | Audio-s per s | Peak VRAM MiB | Preview→full recall@1 | recall@10 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| muq | 10 | 0 | 9.5 | 105 | 4693 | 1.00 | 1.00 |
| muq-mulan | 10 | 0 | 6.8 | 146 | 2859 | 1.00 | 1.00 |
| mert | 10 | 0 | 6.3 | 157 | 3827 | 1.00 | 1.00 |
| clap | 10 | 0 | 6.6 | 150 | 1455 | 0.80 | 1.00 |

- **Recall:** with only 5 candidate tracks, recall@10 is trivially 1.0. Recall@1 is the
  only informative figure here, and CLAP missed one preview.
- **Time:** at these rates, 100 seeds (about 20,000 s of capped audio) take roughly 2 to 3
  minutes per model.
- **Memory:** every model fits well inside 12 GB. MuQ's 4.7 GB peak is the largest, so all
  four should also fit the 1070 Ti's 8 GB. That still has to be measured.
- **Report:** checked in a browser. Verdicts persist across a reload, and the exported
  `verdicts.json` scores correctly. The test verdicts were then discarded.

### 2026-10-26: first benchmark run on the owner's listening history

Run `20261026-223453-0ec1bac`. The seeds are 100 tracks from the owner's ListenBrainz
export (July to October 2026). They are the loved tracks plus the most played (3 to 21
plays), at most two per artist, from 75 artists, mostly melodic bass and future bass.
The seed list stays outside the repo.

- **Acquisition:** 100 of 100 full tracks and 86 previews were fetched. 54 full tracks
  were AcoustID-confirmed. 49 were unverified because AcoustID doesn't know the recording,
  which is common for obscure releases. 2 were `mismatch` and left out of the benchmark,
  which used 194 assets in the end. The first pass missed 54 previews because Deezer lists
  collaborations under their primary artist; credit matching was fixed and the previews
  refetched.
- **Embedding:** 194 of 194 per model, 0 failures, 19,800 s of audio per model. The run
  took 11 minutes for all four models on the RTX 5070.

| Model | Wall s | Audio-s per s | Peak VRAM MiB | Preview→full recall@1 | recall@10 |
| --- | --- | --- | --- | --- | --- |
| muq | 159 | 125 | 4693 | **0.955** | **0.989** |
| muq-mulan | 173 | 114 | 2859 | 0.506 | 0.944 |
| mert | 145 | 137 | 3827 | 0.933 | 0.989 |
| clap | 145 | 137 | 1455 | 0.427 | 0.663 |

Self-retrieval covers the 89 seeds that have both a preview and a full track. CLAP fails
the recall@10 gate of 0.80. MuQ and MERT recognise a 30-second clip of a song almost
perfectly. Gate items 1, 2 and 4 (the owner's judgement) are still open: judge at least
20 seeds in this run's `report.html`, then run `audio-lab score`.

**Owner's decision:** pending.
