# Music analysis research: what embeddings can do for an obscure library

Written 2026-10-31 as the research backing the `add-*` analysis proposals in
`openspec/changes/`. It is a direction document, not a claim that anything works
(`docs/STATUS.md` holds that). **Citations:** the external claims below are from the
author's knowledge of the literature up to 2025 and were not re-verified online in this
session; each proposal's first task re-checks the facts it depends on (licences, model
cards, dataset terms) before code depends on them.

## 1. The constraint that shapes everything

About half the owner's tracks are unknown to AcoustID/MusicBrainz (docs/PRODUCT-VISION.md).
Last.fm tags, Spotify features (403 for new apps, ADR 0003), Discogs genres and
AcousticBrainz (shut down 2022; its dump covers only known recordings) therefore cover
little. Everything must come from **the audio itself** and **the owner's own play
timestamps**. That rules a few things in and out:

- **In:** self-supervised audio embeddings (already in production: MuQ-MuLan, 512-d),
  probes trained on public emotion datasets, zero-shot text prompts through the MuLan text
  tower, classical signal descriptors (tempo, key, loudness, brightness), library-relative
  statistics ("darker than *your* usual"), and behaviour (repeat rate, sessions, hours).
- **Out:** anything whose quality depends on the crowd knowing the song.

## 2. What we already have, measured

| Asset | Evidence |
| --- | --- |
| MuQ-MuLan 512-d vectors for 862 assets, pgvector, exact cosine | docs/AUDIO-BENCHMARK.md, deploy/EMBEDDINGS-ROLLOUT.md |
| Genre precision@10 0.31 (5× chance), co-listening hit 0.13 (4× chance), sleep purity 0.63 (6.7× base) | v2 benchmark run `20261027-031711-c7c3698` |
| Mood probe on DEAM: valence R² 0.615, arousal 0.688 (ridge, 5×5-fold) | run `20261031-204732-9b07ff0`, branch `feat/mood-probe-benchmark` |
| Preview→full recall@1: MuQ 0.96, MuQ-MuLan 0.66 | v2 benchmark |
| GTX 1070: 77 audio-s/s, 2.8 GB peak for MuQ-MuLan | run `20261027-172855` |

The mood result is strong relative to the literature: MARBLE-style linear probes on
EmoMusic typically report arousal R² ≈ 0.70–0.78 and valence R² ≈ 0.55–0.65 for the best
self-supervised models (MERT-330M, Jukebox, MuQ). Our DEAM numbers sit in that band. The
known caveat holds here too: valence and arousal predictions correlate at 0.92 on the
owner's library, so a two-axis chart runs along a diagonal; the "dark-calm vs dark-intense"
corner is where the probe is weakest.

## 3. Open-source model landscape (candidates, with what each adds)

| Model | HF id (check revision) | Licence | Dim | Adds beyond MuQ-MuLan | Fits 1070? |
| --- | --- | --- | --- | --- | --- |
| MuQ-MuLan (in prod) | `OpenMuQ/MuQ-MuLan-large` | CC BY-NC 4.0 | 512 | joint audio–text: zero-shot tags, text search, cluster naming | yes (2.8 GB) |
| MuQ | `OpenMuQ/MuQ-large-msd-iter` | CC BY-NC 4.0 | 1024 | recognition of the same recording across uploads/edits (recall@1 0.96) | yes (5.3 GB; not alongside MuLan) |
| MERT-v1-330M | `m-a-p/MERT-v1-330M` | CC BY-NC 4.0 | 1024 | stronger than 95M on key/chord/beat probes; dropped on duels | likely, fp32 tight |
| LAION CLAP music | `laion/larger_clap_music` | Apache-2.0 | 512 | permissive licence text tower; failed our recall gate | yes |
| Essentia TF models (Discogs-EffNet, MusiCNN heads) | essentia.upf.edu models | CC BY-NC-SA 4.0 (models), AGPL (lib) | – | 400-genre Discogs classifier, mood_happy/sad/aggressive/relaxed/party, danceability, voice/instrumental, tonal/atonal; CPU-cheap | CPU |
| Demucs htdemucs | `facebook/demucs` | MIT | – | vocal stem → vocal presence, lyrics pre-step | yes, slow |
| Whisper large-v3 / faster-whisper | `openai/whisper-large-v3` | MIT | – | lyric transcription (sung WER is high; 30–60% on dense mixes without separation) | large-v3 fp16 no (Pascal fp32 ~10 GB); medium yes |
| Beat This! / BeatNet / madmom | GitHub | MIT / BSD (madmom numpy-2 status uncertain) | – | tempo, beats, downbeats; half/double-time ambiguity on 140/70 BPM dubstep | CPU/GPU |
| All-In-One (Taejun Kim, 2023) | `taejunkim/allinone` | MIT | – | beats + downbeats + segment boundaries + function labels (intro/verse/chorus; no "drop" class) | GPU, moderate |
| Music-understanding LLMs (Qwen2-Audio 7B, SALMONN, LLark, Audio Flamingo) | various | mixed, some non-commercial | – | free-text descriptions; 7B+ in fp32 does not fit 8 GB Pascal; CPU too slow | no |

**Best bets for this project:** (1) keep MuQ-MuLan as the backbone; (2) add MuQ only when
upload-merging is built; (3) Essentia CPU heads as *explainable* secondary descriptors with
non-commercial licence noted; (4) classical descriptors (tempo, key, LUFS, spectral
centroid, sub-bass ratio) which need no training data and are fully traceable; (5) zero-shot
tagging through the text tower, calibrated library-relatively. LLM captioners are not
feasible on the rack and are not needed: nearest-vocabulary naming through the text tower
gives short labels honestly.

## 4. Mood: method and honesty

- **Dataset:** DEAM (1,802 clips, static V/A 1–9, non-commercial CC) is already in use.
  PMEmo (794 pop choruses) and the MTG-Jamendo mood/theme tags are secondary checks, not
  training data, because their terms and label types differ.
- **Known science:** arousal is well predicted from audio; valence is harder, improved by
  mode/key, lyrics and tempo cues. Perceived emotion (what raters hear) ≠ felt mood (what the
  listener feels); the product must say the former and only *test* the latter against
  self-reports.
- **Behavioural evidence worth using:** diurnal and seasonal patterns in valence of streamed
  music (Park et al., Nature Human Behaviour 2019: evening and winter music is lower-arousal
  and lower-valence); generalist/specialist listening diversity (Anderson et al., WWW 2020);
  repeat listening and nostalgia (Conrad et al. 2019); Saarikallio's Music in Mood
  Regulation strategies; Surana et al. 2020 on repetitive sad-music listening as a weak
  depression-risk correlate (Last.fm data). All of these are population-level and weak at
  n = 1, so they justify *which signals to show*, not *what to conclude*.
- **Self-report design:** a one-tap affect grid (valence × energy in one tap) or two 1–5
  reactions in Discord; single-item mood measures are acceptably valid for trend tracking.
  With ~52 weeks a year, report Spearman correlations with n and a bootstrap interval, use a
  trailing 52-week baseline for z-scores, and never show a correlation below n = 8 weeks.
- **Chosen plays only.** Night autoplay sessions (rule validated on the benchmark seeds) are
  excluded by default and shown separately.

## 5. Themes (sound-worlds) and naming

Cluster the library's embeddings (HDBSCAN on cosine, falling back to k-means with silhouette
if HDBSCAN leaves most tracks as noise), keep clusters with ≥ 8 tracks, and name each by
the nearest terms in the MuLan text space from a controlled vocabulary: MTG-Jamendo's 87
genre + 56 mood/theme + 40 instrument tags, plus a curated electronic-subgenre list
(melodic dubstep, future bass, colour bass, wave, phonk, drift phonk, slowed + reverb,
hyperpop, lo-fi hip hop, ambient, drum and bass, liquid dnb, riddim, trance, hardstyle…).
Calibrate: z-score each term's similarity across the library before ranking, so generic
terms ("electronic") don't win every cluster (this counters the modality gap, Liang et al.
2022). Show the top three terms *and* three representative tracks; the user renames
clusters. Weekly theme shares are play-weighted counts per cluster.

## 6. Per-track analysis card (fully explainable facets)

| Facet | Tool | Cost | Pitfall |
| --- | --- | --- | --- |
| Mood V/A | stored MuQ-MuLan probe | free (vectors exist) | diagonal; perceived not felt |
| Tags | zero-shot text tower, calibrated | free | needs vocabulary curation |
| Tempo | Beat This! or librosa, with half/double candidates | CPU seconds | 70/140 ambiguity; slowed edits |
| Key/mode | Essentia KeyExtractor (`edma` profile) or libKeyFinder | CPU | weak on heavily processed bass |
| Loudness | ffmpeg `loudnorm` / pyloudnorm: integrated LUFS, LRA, true peak | CPU | – |
| Brightness, bass weight | spectral centroid; sub-bass (20–120 Hz) energy ratio | CPU | expose as library percentiles |
| Vocals | Essentia voice/instrumental or Demucs vocal-stem ratio | CPU / GPU | ethics: no gender inference |
| Structure | All-In-One or novelty-curve segmentation; "drop" as loudest post-boundary bar | GPU/CPU | no EDM function labels |

Every number carries tool + version; values are shown as percentiles within the user's own
library ("brighter than 82% of what you play"), which is the only frame that is honest
without a crowd.

## 7. Angles beyond the vision document (ranked by value ÷ cost here)

1. **Text search over your own library** ("dark melodic dubstep with female vocals") — one
   text embedding, one cosine query; the stored vectors are already in the joint space.
2. **Forgotten favourites** — tracks with many plays 2+ years ago and none since.
3. **Eras** — change-point detection (PELT) on weekly embedding centroids; names from §5.
4. **Comfort vs exploring** — repeat rate and distance from the long-term centroid, per week.
5. **Upload merging** — MuQ self-retrieval to fold slowed/sped-up edits into one recording
   (follow-up change; needs MuQ in production).
6. **Discovery from previews** — score Deezer previews of new releases against the taste
   distribution (cold-start content-based recommendation, Van den Oord et al. 2013 lineage).
7. **Club bridge songs** — tracks near two members' distributions as nomination suggestions.
8. **Sonic colour** — deterministic PCA→OKLAB palette per track/week for cards.
9. **Lyrics themes** — Demucs + Whisper; expensive on Pascal, optional and last.
10. **Interpretability** — per-window similarity ("the drop is what these share") from the
    10 s windows the pipeline already computes.

## 8. Presentation (see `docs/research/MOCKUPS.md`)

Patterns borrowed from the products people share and trust: Wrapped's shareable cards and
"phases"; Last.fm/ListenBrainz listening clocks and per-week reports; Plexamp's sonic
sliders; Exist.io's correlations with strength labels and n. Anti-patterns to avoid: fake
precision, personality-type labels, saying "you are sad", charts drawn from placeholders.
Copy patterns: "Your music was darker than usual this week (−1.3 σ against 52 weeks; 61 of
84 chosen plays had audio)."; "Not enough listening with audio this week to say."
