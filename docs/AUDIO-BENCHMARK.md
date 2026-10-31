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

1. **Duels judged:** at least **40** blind duels answered in the report's Duels tab.
2. **Win rate:** the highest duel win rate of the run, and at least **0.55**
   (`audio-lab score`; a tie counts as half a win).
3. **Self-retrieval:** preview→full recall@10 of at least **0.80** (from `metrics.json`),
   where previews exist.
4. **Owner's decision:** recorded below with the run ID. Nothing passes automatically. If
   the top two win rates are within 0.05, the owner chooses between them on cost and
   capability.

The other automatic metrics (same-artist rate, separation, overlap) are evidence for the
decision, not gates.

The thresholds are a starting point. Change them here with a dated note, never silently.

- **2026-10-26:** the gate moved from good/bad verdicts (20 seeds, agreement of 0.70 or
  more) to blind duels. On the owner's library every model's list sounded reasonable, so
  verdicts couldn't separate models that share only 22–44% of their neighbours.

Integration also requires timing on the rack's GPU. That's a GTX 1070, recorded as a
1070 Ti until 2026-10-27. Timing it needs a separate PyTorch environment, because CUDA
12.8+ builds dropped Pascal. It was measured in run `20261027-172855-0c32766-dirty`
(below).

## Mood gate

The duel gate chose a model for neighbours. This one asks whether embeddings can predict
perceived mood, using DEAM's static ratings and linear probes (`audio-lab mood-probe`). Fixed on
2026-10-31, before any mood result existed. A model passes only when **all** of these hold on
one run:

1. **Arousal:** cross-validated R² of at least **0.50**, above the mean-only baseline.
2. **Valence:** cross-validated R² of at least **0.35**, above the mean-only baseline.
3. **Owner's listening check:** the top and bottom 20 of the owner's library on each dimension
   sound broadly right.
4. **Owner's decision:** recorded below with the run ID.

A model counts as ahead of another only when the 95% interval of their paired difference excludes
zero. A tie keeps the model already in production. If nothing passes, weekly profiles must not
present mood as a measured value.

Change these thresholds here with a dated note, never silently.

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
  four should also fit the rack GPU's 8 GB. That still had to be measured; see the GTX
  1070 run below.
- **Report:** checked in a browser. Verdicts persist across a reload, and the exported
  `verdicts.json` scores correctly. The test verdicts were then discarded. (This was the
  first report version; duels replaced verdicts the same day.)

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
perfectly.

A first pass at judging showed that every model's list sounded reasonable, so the report
was rebuilt around blind duels and these automatic metrics (`metrics.json`, recomputed
from the same embeddings):

| Model | Same artist in top 10 | Separation |
| --- | --- | --- |
| muq | 27% | 0.239 |
| muq-mulan | **37%** | **0.325** |
| mert | 29% | 0.070 |
| clap | 23% | 0.063 |

- **Same artist:** over the 61 seeds whose artist has another seed. It's the share of
  those other songs that appear in the seed's top 10.
- **Separation:** the mean gap between a seed's best and median similarity. MERT and CLAP
  give nearly every track the same similarity, so they barely tell this library apart.
- **Overlap:** the top-10 lists share 22% (CLAP and MuQ-MuLan) to 44% (MERT and MuQ) of
  their neighbours. The models agree that the songs are close, but disagree on which
  songs are closest.

The report has 630 duels: each of 105 seeds against 6 model pairs. 559 of them compare
rank-1 picks.

**Duels (2026-10-27):** the owner answered 81 blind duels (`duels.json` and `scores.json`
are in the run directory).

| Model | Win rate | Won | Lost | Tied |
| --- | --- | --- | --- | --- |
| muq | **0.65** | 20 | 8 | 13 |
| muq-mulan | 0.61 | 20 | 11 | 9 |
| mert | 0.43 | 11 | 17 | 13 |
| clap | 0.31 | 6 | 21 | 13 |

| Pair | Result (wins–wins–ties) |
| --- | --- |
| muq vs muq-mulan | 9–3–2 |
| muq vs mert | 4–4–6 |
| muq vs clap | 7–1–5 |
| muq-mulan vs mert | 10–0–3 |
| muq-mulan vs clap | 7–2–4 |
| mert vs clap | 7–3–4 |

- **Uncertainty:** each model has about 40 duels, so a win rate is good to roughly ±0.15.
  Only muq-mulan's 10–0 over MERT is clear on its own (sign test p < 0.01). MuQ's 9–3 over
  muq-mulan points the same way as the overall ranking but isn't conclusive (p ≈ 0.15).
- **Gate:**
  - **Items 1 and 3 pass:** 81 duels were answered, and MuQ's recall@10 is 0.989.
  - **Item 2 passes for MuQ:** it has the top win rate, and 0.65 is above 0.55.
  - **Item 4 is the owner's choice:** MuQ and muq-mulan are 0.04 apart, inside the 0.05
    margin, so cost and capability decide.
- **The trade-off between the two:**
  - **MuQ:** wins the head-to-head and recognises previews far better (recall@1 0.955
    against 0.506).
  - **muq-mulan:** groups artists better and separates the library more sharply. It is
    also the only model with a text tower, which would allow a search like "dark melodic
    dubstep".
- **MERT and CLAP are out.** CLAP fails recall, and MERT loses to both MuQ models.

**Owner's decision (2026-10-27):** MuQ leads provisionally. Its 0.65 win rate against
MuQ-MuLan's 0.61 is inside the 0.05 margin, and the owner judged the seed set too narrow
and dirty to decide on: one recent genre, two podcast episodes, and unlabelled sleep
tracks. The final pick between MuQ and MuQ-MuLan is deferred to the v2 benchmark
(`add-audio-benchmark-v2`). MERT and CLAP are dropped.

### 2026-10-27: v2 benchmark: cleaned history plus a genre control set

Run `20261027-031711-c7c3698` (`add-audio-benchmark-v2`).

**Seeds:**
- **Personal:** 250 seeds from the owner's full ListenBrainz export (74,826 listens, 2019–2026).
  - **Removed:** 83 listens over 10 minutes, 7 podcast listens and 386 YouTube Labs listens.
  - **Channel uploads** titled "Artist - Title" are credited to the real artist.
  - **Sleep tracks:** 37 seeds are labelled sleep. Their plays fall mostly in the 84 long night sessions, which are sleep-tab autoplay.
  - **Balance:** at most 2 per artist, spread across first-play years 2019–2026, with 57 pairs of songs the owner often plays back to back.
- **Genre control set:** 150 tracks, 10 from each of 15 Deezer genre charts.

**Acquisition:**
- **Coverage:** 384 of 399 seeds have audio: 341 full tracks and 363 previews, 704 assets after removing 15 mismatches.
- **Missing full tracks:** about 30 of the owner's songs have none. Their YouTube uploads are gone, and an explicit video ID never falls back to search.
- **Too long:** one 90-minute mix was skipped by `--max-duration 600`.

**Embedding:** RTX 5070, about 70,600 s of audio per model, 28 minutes for all four models.

| Model | Wall s | Audio-s per s | Peak VRAM MiB |
| --- | --- | --- | --- |
| muq | 411 | 172 | 4693 |
| muq-mulan | 434 | 163 | 2859 |
| mert | 352 | 201 | 3827 |
| clap | 441 | 160 | 1455 |

**Automatic metrics** (`metrics.json`). The "Chance" column is what random neighbours would score.

| Metric | muq | muq-mulan | mert | clap | Chance |
| --- | --- | --- | --- | --- | --- |
| Preview→full recall@1 (319 seeds) | **0.962** | 0.658 | 0.950 | 0.245 | – |
| Preview→full recall@10 | **0.991** | 0.915 | 0.975 | 0.436 | – |
| Genre precision@10 (150 control seeds) | 0.215 | **0.313** | 0.173 | 0.086 | ~0.06 |
| Co-listening hit rate (51 pairs) | 0.118 | **0.127** | 0.078 | 0.010 | ~0.03 |
| Sleep purity (36 sleep seeds) | 0.625 | **0.628** | 0.431 | 0.319 | 0.094 |
| Same-artist rate (153 seeds) | **0.295** | 0.213 | 0.195 | 0.136 | – |
| Separation | 0.223 | **0.405** | 0.055 | 0.043 | – |

- **Finalists:** MuQ and MuQ-MuLan lead every metric except recall, where MERT is close behind MuQ. CLAP stays out, failing recall@10 again at 0.44.
- **Genre:** MuQ-MuLan separates genres best, about 5 times chance, against MuQ's 3.5. Deezer's chart labels are noisy (a Shakira track charts under Rap/Hip Hop, for example), so the absolute figures are low for every model.
- **Taste and mood:** MuQ and MuQ-MuLan are even on co-listening (12% and 13%, about 4 times chance) and on sleep purity (0.63 each, about 6.7 times the base rate).
- **Recognition and artist:** MuQ is clearly better at recognising a song from its preview and at grouping an artist's songs.
- **Overlap:** the two finalists share 32% of their top-10 neighbours.

**Finalist duels** (`audio-lab score`, 103 of 384 duels judged on 2026-10-27):

| Seeds | Duels | MuQ wins | MuQ-MuLan wins | Ties | MuQ-MuLan win rate |
| --- | --- | --- | --- | --- | --- |
| All | 103 | 25 | 35 | 43 | **0.55** |
| Personal | 55 | 23 | 27 | 5 | 0.54 |
| Genre control | 47 | 1 | 8 | 38 | 0.57 |
| Sleep (within personal) | 9 | 1 | 1 | 7 | 0.50 |

- **Personal seeds** are close to even: 27 against 23, which a coin would beat or match two times in three (sign test p ≈ 0.67).
- **Genre control seeds** are mostly ties, and MuQ-MuLan wins nearly all the rest, 8 to 1 (p ≈ 0.04). This agrees with its genre precision.
- **Overall,** 35 against 25 decisive duels is suggestive, not conclusive (p ≈ 0.25).

**Gate v2:**
- **Items 1 and 3 pass:** 103 duels were judged, and MuQ-MuLan's recall@10 is 0.915.
- **Item 2 passes for MuQ-MuLan,** just: it has the top win rate, and 0.55 meets the threshold.
- **Item 4:** the two are 0.10 apart, outside the 0.05 margin, so the owner's decision is a yes or no on MuQ-MuLan.

**Owner's decision (2026-10-27):** MuQ-MuLan passes and becomes the lead model, because it
can do more: its joint audio–text space allows text queries and descriptions, and it leads
on genre. MuQ is kept as a second model for now, for song recognition and artist grouping,
where it is clearly stronger, and because the two tie on the owner's own songs. Integration
(pgvector, `gpu` queue) starts with MuQ-MuLan. Whether MuQ is embedded in production too is
decided in that change. MERT and CLAP stay dropped.

### 2026-10-27: GTX 1070 timing on docker-0

Run `20261027-172855-0c32766-dirty` (`measure-audio-models-on-1070ti`). It's the v2 manifest
(the same SHA-256, 704 assets) on the rack's GPU, embedded with MuQ-MuLan and MuQ only. The
`-dirty` suffix means it ran from that change's uncommitted audio-lab code at `0c32766`.

- **Environment:**
  - docker-0, Ubuntu 26.04 VM, GeForce GTX 1070 (compute capability 6.1, 8 GB) passed
    through from stache-0, driver 580.178.04.
  - The audio-lab `models-pascal` image: torch 2.11.0+cu126 (built for `sm_50`–`sm_90`),
    torchvision 0.26.0+cu126, Python 3.11.18, fp32.
  - Audio staged on docker-0's root disk.
- **Weights** were downloaded by a one-asset warm-up first, so the load times are from a
  warm cache in a fresh process, as a production job would see them.

| Model | Wall s | Audio-s per s | vs RTX 5070 | Load s | Peak VRAM MiB | Embedded | Failed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| muq-mulan | 919 | 76.9 | 2.1× slower | 13.6 | 2756 | 703 | 1 |
| muq | 915 | 77.2 | 2.2× slower | 2.1 | 5332 | 703 | 1 |

- **Failures:** the one failure per model is the same 90-minute mix skipped by
  `--max-duration 600`, as in run `20261027-031711-c7c3698`.
- **Memory:**
  - MuQ-MuLan peaks well inside 8 GB.
  - MuQ peaks higher than on the RTX 5070 (5,332 against 4,693 MiB), but still fits.
  - Together they'd need about 8.1 GB, so on this card the two can't be resident at once.
    Swarm doesn't reserve the GPU, so any other GPU service on docker-0 shares the same 8 GB.

**Parity with the RTX 5070** (`audio-lab parity`, run `20261027-031711-c7c3698` against this
one, 703 shared assets each):

| Model | Min cosine | 1st percentile | Median | Below 0.999 |
| --- | --- | --- | --- | --- |
| muq-mulan | 0.999993 | 0.999999 | 1.000000 | 0 |
| muq | 0.999983 | 1.000000 | 1.000000 | 0 |

The vectors are the same model across two GPUs, two CUDA runtimes, two operating systems
and two ffmpeg builds: every asset agrees to at least 0.99998. The integration's parity
threshold of 0.999 holds with a wide margin.

**Sizing `analysis.embed_audio`** (Decision 7 of the change):
- **Worst case:** a full track capped at 180 s takes 180 / 76.9 ≈ 2.34 s. A batch of 128
  then takes at most 13.6 + 128 × 2.34 ≈ 313 s, about a sixth of an 1,800 s limit, so the
  limit stays at 1,800 s.
- **Typical:** this library's assets average 100 s, so a typical batch is about 3 minutes.
- **Batch size:** 128 keeps the model load to about 4% of a worst-case batch, and limits
  the re-done work when a batch is retried. The rule (a batch at most half its limit) would
  allow up to about 375.
- **Backfill cost:** at this library's average length, MuQ-MuLan takes about 22 minutes per
  1,000 assets. Embedding MuQ as well would add about 22 minutes per 1,000. The owner kept
  MuQ out of the integration regardless.

### 2026-10-27: production parity on docker-0

`add-muq-mulan-embeddings` reimplements MuQ-MuLan's decoding, windowing, inference and
pooling inside Sidetrack (`sidetrack.analysis.embeddings`). Its GPU parity test
(`services/gpu-worker/tests/test_parity.py`) ran in the `sidetrack-gpu` test image on
docker-0's GTX 1070. That image has torch 2.11.0+cu126 and numpy 1.26.4, where the
benchmark had numpy 2.3.5.

- **Sample:** 24 assets spread across run `20261027-031711-c7c3698`, previews and full
  tracks alike.
- **Result:** every production vector matched the benchmark run's MuQ-MuLan vector for the
  same SHA-256, with a minimum cosine of 1.000000 at six decimals. The spec's threshold is
  0.999. The test took 99 s, including the weight download.

## Rack backfill, 2026-10-31

The owner's library is embedded in production: 862 of 862 assets, on the rack's GTX 1070, at
revision `2e01c796b71dca71b45251384c04cd7b237c9020`. The 861 assets of the main backfill took 21
minutes in 7 jobs, with no failures or retries. Spot checks returned same-genre neighbours. See
[the rollout record](../deploy/EMBEDDINGS-ROLLOUT.md).

### 2026-10-31: mood probes on DEAM

Run `20261031-204732-9b07ff0`: all 1,802 DEAM clips, with 0 failures. Environment: RTX 5070,
torch 2.11.0+cu128, 118 audio-s/s for each model. Five repeats of 5-fold nested cross-validation.

| Model | Valence R² | Arousal R² | Mean R² |
| --- | --- | --- | --- |
| `muq-mulan` | 0.615 | 0.688 | 0.652 |
| `muq` | 0.564 | 0.658 | 0.611 |
| Mean-only baseline | -0.001 | -0.001 | -0.001 |

MuQ-MuLan is ahead of MuQ by 0.040 mean R² (95% interval 0.028 to 0.054). Both models clear the
gate's two numeric thresholds. The owner's listening check and decision are still to come.

- **Data source:** DEAM's official site (Aljanaki, Yazdani and Soleymani, 2017) timed out, so the
  owner downloaded the audio from a Kaggle copy and the ratings from a separate copy. All 1,802
  rated clips matched an audio file, and the count and columns match the published dataset. The
  dataset's licence is non-commercial Creative Commons. Nothing from it is in this repo.
- **No artist grouping:** the metadata file wasn't available, so each clip is its own group. Clips
  by one artist can sit on both sides of a split, which may flatter these scores. Both models get
  the same benefit, so the comparison is fairer than the absolute numbers.
- **Valence and arousal are less separate than the scores suggest.** Human ratings correlate at
  0.57, MuQ-MuLan's held-out predictions at 0.83, and its predictions on the owner's library at
  0.92. It still predicts 27% of the valence that arousal doesn't explain, and 34% of the arousal
  that valence doesn't explain (MuQ: 17% and 26%), so the two aren't the same signal, but dark and
  calm tracks will often be hard to tell apart. A two-axis mood chart will tend to run along a
  diagonal.

