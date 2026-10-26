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

### First judged run

Not run yet. It needs the owner's ~100-seed list fetched with
`python -m sidetrack.audio fetch` (see `docs/AUDIO.md`), then `embed`, `report`,
judging at least 20 seeds, and `score`.
