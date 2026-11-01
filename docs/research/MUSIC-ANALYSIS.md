# Music analysis research: what embeddings can do for an obscure library

Written 2026-10-31 as the research backing the `add-*` analysis proposals in
`openspec/changes/`. It is a direction document, not a claim that anything works
([STATUS](../STATUS.md) holds that). The
[detailed research notes](MUSIC-ANALYSIS-RESEARCH-NOTES.md) preserve the recovered
agent findings, checked sources, licensing caveats and follow-ups to the proposals.
Re-check the exact checkpoint, dataset terms and product behavior before relying on
them; the notes distinguish evidence from hypotheses.

None of the claims below may reach a user until it passes its gate: the register and dataset
rights are in [docs/evaluations/](../evaluations/README.md).

## 1. The constraint that shapes everything

About half the owner's tracks are unknown to AcoustID/MusicBrainz
([PRODUCT-VISION](../PRODUCT-VISION.md)). Per-track community tags and popularity
therefore cannot be assumed to exist. Spotify's 2024 restrictions also limit its audio
features for new use cases, with an exception for existing extended-mode access
([announcement](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api));
Sidetrack uses Spotify for metadata only. The analysis should work from **the audio
itself** and **the owner's own listening history**, without requiring a crowd to have
tagged each obscure track:

- **In:** self-supervised audio embeddings (already in production: MuQ-MuLan, 512-d),
  probes trained on public emotion datasets, zero-shot text prompts through the MuLan text
  tower, classical signal descriptors (tempo, key, loudness, brightness), library-relative
  statistics ("darker than *your* usual"), and behaviour (repeat rate, sessions, hours).
- **Out:** anything whose quality depends on the crowd knowing the song. This does not
  mean the models and evaluation datasets have no human-created training labels.

## 2. What we already have, measured

| Asset | Evidence |
| --- | --- |
| MuQ-MuLan 512-d vectors for 862 assets, pgvector, exact cosine | docs/AUDIO-BENCHMARK.md, deploy/EMBEDDINGS-ROLLOUT.md |
| Genre precision@10 0.31 (5× chance), co-listening hit 0.13 (4× chance), sleep purity 0.63 (6.7× base) | v2 benchmark run `20261027-031711-c7c3698` |
| Mood probe on DEAM: valence R² 0.615, arousal 0.688 (ridge, five repeats of nested 5-fold CV) | run `20261031-204732-9b07ff0`, branch `feat/mood-probe-benchmark`; owner gate pending |
| Preview→full recall@1: MuQ 0.96, MuQ-MuLan 0.66 | v2 benchmark |
| GTX 1070: 77 audio-s/s, 2.8 GB peak for MuQ-MuLan | run `20261027-172855` |

The DEAM splits were **not artist-grouped**, because artist metadata was unavailable;
that can inflate the absolute scores. Do not compare them directly with published
results that use different data or splits. On the owner's library the two predictions
correlate at 0.88, so the two-axis view may run along a diagonal. The owner's listening
check and decision are still pending. The production pipeline stores one pooled vector
per asset, not the intermediate 10-second window vectors.

## 3. Model landscape (open-source code and open-weight candidates)

| Candidate | Licence and dimensions | Potential role and limits |
| --- | --- | --- |
| [MuQ-MuLan](https://huggingface.co/OpenMuQ/MuQ-MuLan-large) | MIT code; CC BY-NC 4.0 weights; 512-d locally | Accepted production audio backbone. Joint text search and tags need integration and task-specific evaluation. Measured on the 1070 at 2.8 GB peak. |
| [MuQ](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter) | CC BY-NC 4.0 weights; 1024-d locally | Preview-to-full recall@1 was 0.96 in the v2 benchmark. Not enabled in production; slowed edits and recording identity need separate tests. Measured at 5.3 GB peak. |
| [MERT](https://huggingface.co/m-a-p/MERT-v1-330M) | CC BY-NC 4.0 weights; 95M is 768-d, 330M is 1024-d | Potential task-specific features. Sidetrack's benchmark dropped the **95M** model on neighbour duels; the 330M model and its rack fit were not measured. |
| [LAION CLAP music](https://huggingface.co/laion/larger_clap_music) | This checkpoint's card says Apache-2.0; 512-d locally | Joint text/audio alternative. It failed the local preview/full retrieval gate; that does not prove it cannot be useful for other text-retrieval tasks. |
| [Essentia and MTG models](https://essentia.upf.edu/models.html) | AGPLv3 library; model terms need clarification | Classical features and candidate mood, style, instrument and vocal-presence heads. The models page and license file contain conflicting NC-SA/NoDerivatives wording; verify each weight with the licensor. |
| [Beat This!](https://github.com/CPJKU/beat_this) / [madmom](https://github.com/CPJKU/madmom) | Check code and model terms separately | Beat/downbeat tracking; half/double-time ambiguity and underrepresented genres need testing. Madmom's code is BSD, but its model/data files are CC BY-NC-SA. Rack cost is unmeasured. |
| [All-In-One](https://github.com/mir-aidj/all-in-one) | Check the package, weights and dependencies separately | Beats, downbeats, boundaries and labels such as intro/verse/chorus; **no drop class**. NATTEN and rack compatibility need testing. |
| [Demucs](https://github.com/facebookresearch/demucs) / [Whisper](https://github.com/openai/whisper) | Check each component and weights | Optional source separation and speech recognition. Sung-lyrics accuracy and rack cost are unmeasured; the original Demucs repo is no longer actively maintained. |
| Music-understanding LLMs | Mixed terms; check per model | Free-text descriptions are a later experiment. Large fp32 models exceed the 8 GB GPU; quantized alternatives, quality and latency remain unmeasured. |

**Best bets to investigate:** retain MuQ-MuLan under ADR 0010; evaluate classical
descriptors and text search against real tracks; consider MuQ for recognition candidates
only after identity testing. Other heads require licensing and hardware checks. A
library-relative text score may aid ranking, but it does not establish calibration or
guarantee that a label is correct. Keep any LLM captioning optional until measured.

## 4. Mood: method and honesty

- **Data:** the experimental probe used DEAM's 1,802 recordings/excerpts and static
  nine-point ratings. Check the rights for the exact audio and annotation artifacts.
  PMEmo and MTG-Jamendo are possible secondary checks, but their labels and terms differ.
- **Meaning:** perceived emotion (what raters hear in the music) is not felt mood (what
  the listener feels). A population study of
  [time-of-day listening patterns](https://research.atspotify.com/publications/global-music-streaming-data-reveals-robust-diurnal-and-seasonal-patterns-of-affective-preference)
  suggests questions, not individual conclusions or diagnoses.
- **Self-report:** an optional private affect check-in could support exploratory
  associations. Define the timing and report n, coverage and appropriate uncertainty;
  handle ties, constant values, repeated observations and temporal dependence. The
  draft's eight-week minimum is a product threshold, not evidence that correlations
  are reliable. No fixed number of future observations guarantees a narrower interval.
- **Session filtering:** late-night autoplay is a heuristic, not proof of intent or
  sleep. Flag sessions visibly, let the user correct them, and disclose any exclusions.

## 5. Themes (sound-worlds) and naming

Experiment with clusters of a user's eligible embeddings and candidate names from a
versioned, curated vocabulary, including terms relevant to their music. MTG-Jamendo's
split vocabulary offers 87 genre, 56 mood/theme and 40 instrument terms, but its tags
are uploader-supplied and may not cover an obscure electronic library. Compare HDBSCAN
and simpler baselines, noise thresholds and stability across runs; do not force a
cluster when the evidence is weak. Per-term library z-scores are a ranking heuristic,
**not a proven correction for the audio/text modality gap** or calibrated confidence.
Show candidate terms and representative tracks, allow abstention and user renames, and
record the eligible tracks and denominator behind weekly shares.

## 6. Per-track analysis card (candidate facets)

| Facet | Tool | Cost | Pitfall |
| --- | --- | --- | --- |
| Mood V/A | MuQ-MuLan probe, if approved | CPU scoring proposed | diagonal; perceived not felt; owner gate pending |
| Tags | zero-shot text tower | integration required | prompt and vocabulary sensitivity; not probabilities |
| Tempo | Beat This! or librosa, with half/double candidates | measure locally | 70/140 ambiguity; slowed edits |
| Key/mode | Essentia KeyExtractor or another evaluated method | measure locally | may be weak or inapplicable on processed/atonal tracks |
| Loudness | ffmpeg `loudnorm` / pyloudnorm | measure locally | mastering, source and analyzed duration matter |
| Brightness, bass weight | spectral centroid; stated bass-band energy ratio | measure locally | a percentile is relative to the user's eligible library |
| Vocals | evaluated voice/instrumental classifier or separation | measure locally | uncertain estimates; no gender inference |
| Structure | All-In-One or novelty-curve segmentation | measure locally | candidate boundaries are not automatically EDM drops |

Every number needs its tool and version, source, analyzed duration and appropriate
uncertainty. A percentile must identify the user's eligible reference library; absolute
measurements can also be shown with their units and method.

## 7. Angles beyond the vision document (ranked by value ÷ cost here)

1. **Text search over your own library** — evaluate phrases such as “dark melodic bass
   with airy vocals” against the stored joint-space vectors.
2. **Forgotten favourites** — resurface earlier heavily played tracks, with historical
   import coverage and a clearly stated time window.
3. **Eras and exploration** — compare weekly profiles and candidate change-points against
   a personal baseline; never imply an inferred life event.
4. **Version discovery** — retrieve candidate related recordings for user review. MuQ's
   preview benchmark does not justify automatically merging slowed or sped-up edits.
5. **Discovery from previews** — rank appropriately acquired previews against listening
   examples, while disclosing preview coverage and acquisition restrictions.
6. **Club bridge songs** — suggest nominations near two consenting members' eligible
   libraries, with coverage shown for both.
7. **Sonic colour** — a deterministic palette for cards, accompanied by labels and
   non-color alternatives.
8. **Lyrics themes** — an optional later experiment requiring transcription evaluation
   and rights review, not a guaranteed Whisper capability.
9. **Section-level “why”** — requires new timestamped vectors and alignment tests; the
   current pooled vectors cannot identify a shared drop.

## 8. Presentation (see `docs/research/MOCKUPS.md`)

Patterns worth exploring include shareable cards and timelines, recurring listening
reports, sonic neighbours and drill-down into the tracks behind a result. Avoid fake
precision, personality-type labels, “you are sad,” and charts drawn from placeholders.
Example copy: “Your music was darker than usual this week (−1.3 σ against your eligible
52-week baseline; 61 of 84 counted plays had usable mood analysis).” Or: “Not enough
listening with usable analysis this week to say.”
