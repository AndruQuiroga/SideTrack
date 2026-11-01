# Music analysis: research evidence and recovered findings

Reviewed 2026-10-31. This is the detailed companion to
[Music analysis research](MUSIC-ANALYSIS.md) and
[the mockups](MOCKUPS.md). It is research and product exploration, not an
implementation claim; [STATUS](../STATUS.md) is authoritative for what works.

## What was recovered and how to read it

One nested research agent completed a detailed survey of music-analytics products. Its
parent agents did not return final reports, but substantial source calls and partial
findings from other nested agents survived in session history. The useful findings are
consolidated below rather than presented as completed reports. Directly checked papers,
model cards, project documentation and product pages are linked alongside the claims;
vendor descriptions establish what a product says, not independent evidence of quality.
Where a page was inaccessible, the item is marked as a lead rather than a verified
feature. Online pages and licenses can change, so check the exact revision before use.

**The requirement is audio-derived inference for a track without needing other people to
have tagged or played that track.** It does not imply that a pretrained model, its
training data, or its evaluation datasets are free of human-created labels. DEAM uses
human emotion annotations; MTG-Jamendo's tags were supplied by uploaders. An owner's
own listens and optional corrections are useful personal data, not a population-wide
popularity signal. Sound can suggest a genre term, but genre also has cultural and
community meaning that an audio model cannot establish by itself.

## 1. What Sidetrack has and what it does not

- Production holds 862 imported audio assets with MuQ-MuLan vectors and can return
  neighbours from pgvector. No HTTP route or page uses those embeddings yet.
  ListenBrainz import, per-track mood scores, themes, weekly profiles and compatibility
  remain proposals or stubs. See [STATUS](../STATUS.md),
  [the embedding rollout](../../deploy/EMBEDDINGS-ROLLOUT.md), and
  [ADR 0010](../decisions/0010-muq-mulan-audio-embeddings.md).
- The production pipeline decodes mono audio, uses non-overlapping 10-second windows,
  keeps a final partial window of at least three seconds, caps full tracks at their first
  180 seconds, then mean-pools and L2-normalizes **one vector per asset**. A file shorter
  than three seconds is kept as one short window. See
  [the model registry](../../sidetrack/analysis/embeddings/registry.py) and
  [windowing and pooling](../../sidetrack/analysis/embeddings/audio.py). The windows are
  not stored as timestamped vectors. A result based on the first three minutes does not
  describe later sections, and a preview and a full recording need not represent the
  same section.
- Audio-to-track resolution is a separate proposed step; an audio asset does not by itself
  prove that a listening event is linked to it. Show coverage, unresolved identities,
  preview/full status and analyzed duration before making library-wide claims.
- The accepted deployment has a shared 8 GB GTX 1070. The recorded MuQ-MuLan test was
  about 77 audio-seconds/second and 2.8 GB peak VRAM in its specified environment; it
  is not a guarantee of end-to-end throughput or simultaneous-model capacity. The
  project's approximate **40 GB SSD budget is a budget, not measured free space**;
  audio and backups belong on HDD. Measure CPU, GPU, scratch space, cold-start and
  coexistence with other services before choosing another model. See
  [the benchmark](../AUDIO-BENCHMARK.md) and
  [ADR 0005](../decisions/0005-musicbrainz-mirror-and-storage-budget.md).
- The same run measured about 5.3 GB peak VRAM for MuQ. Its peak plus MuQ-MuLan's
  approaches or exceeds the card's practical capacity, so their individual
  measurements are not evidence that both can safely remain resident together. A
  three-minute input at the MuQ-MuLan benchmark rate corresponds to about 2.3 seconds
  of benchmarked work in idealized arithmetic, not an end-to-end job-time promise.
- For scale only, 862 vectors of 512 float32 values contain about 1.7 MiB of raw
  numbers. Eighteen such vectors per asset would be about 30 MiB if every asset had
  three minutes of windows. PostgreSQL rows, indexes, revisions and other metadata
  add overhead, and actual assets have different durations; neither estimate is a
  measured database or backup size.
- The separate infrastructure review recorded the GPU VM configured with 24 GiB RAM
  in October 2026 (about 22 GiB visible to its guest), shared with Minecraft containers
  whose limits totaled 15 GiB. Swarm did not reserve the GPU between services.
  These are dated configuration observations, not current available capacity; check
  actual memory pressure and concurrent workloads before running experiments.
- Audio acquisition remains explicitly opt-in and personal. Never schedule yt-dlp,
  serve audio over HTTP, or send a private library to an external analysis service.
  Dataset references below are not permission to download or redistribute their audio.
  [ADR 0007](../decisions/0007-audio-acquisition-yt-dlp.md) governs acquisition.

## 2. Models and analysis methods

These are candidates for different jobs, not a single leaderboard. A feature requires a
specific model/checkpoint, task, input pipeline, output interpretation, license and
evaluation; a good neighbour embedding does not automatically make a good beat tracker,
tagger or recommendation system.

| Candidate | What it could contribute | Evidence and limitations |
| --- | --- | --- |
| [MuQ-MuLan](https://huggingface.co/OpenMuQ/MuQ-MuLan-large) | Joint audio/text search, descriptive labels and a reusable audio embedding. | The accepted 512-dimensional production model. The card identifies MIT code and CC BY-NC 4.0 weights. Text encoding and product search still need integration and evaluation. |
| [MuQ](https://huggingface.co/OpenMuQ/MuQ-large-msd-iter) | An audio-only representation that was stronger at preview-to-full retrieval in the local benchmark. | 1,024-dimensional in Sidetrack's benchmark, CC BY-NC 4.0 weights, not enabled in production. Preview retrieval is not evidence that altered-speed edits or covers can be merged safely. |
| [MERT 95M and 330M](https://huggingface.co/m-a-p/MERT-v1-330M) | Alternative music representations; features from different layers may suit different downstream tasks. | The card gives 768 dimensions/12 layers for 95M and 1,024/24 for 330M, with CC BY-NC 4.0 weights. The local neighbour benchmark tested **95M**, not 330M; the larger model's rack fit and task performance are unmeasured. |
| [MusicFM](https://github.com/minzwon/musicfm) | Frame-level features for beat, chord, structure or tagging experiments. | The authors describe different temporal resolutions and layer choices for different tasks; sequence averaging loses timing. Check each checkpoint and its license separately; no Sidetrack benchmark yet. |
| [LAION CLAP music](https://huggingface.co/laion/larger_clap_music) | A different joint audio/text space for comparison. | This checkpoint's card says Apache-2.0; check the separate code license. It failed Sidetrack's preview/full retrieval gate, which does **not** establish that it fails every text-search task. |
| [Essentia](https://github.com/MTG/essentia) and [MTG models](https://essentia.upf.edu/models.html) | Classical descriptors and pre-trained instrument, mood, style or vocal-presence heads. | Essentia's library is AGPLv3. The models page says CC BY-NC-SA, while its [license file](https://essentia.upf.edu/models/LICENSE) contains conflicting NoDerivatives and ShareAlike wording. Verify each weight and ask the licensor before integration or adaptation. Cost and accuracy on this library are unmeasured. |
| [Beat This!](https://github.com/CPJKU/beat_this) | Beat and downbeat timestamps, with tempo estimated from the beat sequence. | MIT-licensed repository; its [paper](https://arxiv.org/abs/2407.21658) acknowledges failures on difficult and underrepresented genres. CPU/GPU cost and Pascal compatibility need a local test; half/double-tempo alternatives matter. |
| [madmom](https://github.com/CPJKU/madmom) | Existing beat/downbeat and other MIR algorithms. | Its [license](https://raw.githubusercontent.com/CPJKU/madmom/main/LICENSE) distinguishes BSD-licensed code from CC BY-NC-SA 4.0 model/data files. Check Python/NumPy compatibility and dependency licenses. |
| [All-In-One](https://github.com/mir-aidj/all-in-one) | Candidate beats, downbeats, section boundaries and labels such as intro, verse and chorus. | Its [paper](https://arxiv.org/abs/2307.16425) uses demixed audio. It has no EDM-specific drop/build/breakdown label; Linux/Windows require NATTEN. Pascal compatibility, storage and latency are unmeasured. |
| [Demucs](https://github.com/facebookresearch/demucs) and [Whisper](https://github.com/openai/whisper) | Optional source separation and speech-recognition experiments, potentially supporting lyric analysis. | Demucs' original repository says it is no longer actively maintained. Whisper is speech recognition, not reliable lyric transcription by definition. Measure word error and hallucinations on singing, language and mixes; check rights to retain or display lyrics. |
| [Chromaprint](https://github.com/acoustid/chromaprint), [MOVE](https://github.com/furkanyesiler/move), [CoverHunter](https://github.com/Liu-Feng-deeplearning/CoverHunter) | Three different identity/version tasks: near-identical audio fingerprints, or discovery of recordings related by an underlying musical work. | Chromaprint targets near-identical audio; MOVE and CoverHunter target version/cover retrieval, not proof of the same recording. Their code, model and data terms, dependencies and accuracy require separate review. |

The [MuQ paper](https://arxiv.org/abs/2501.01108) reports strong downstream results,
but the model card warns that released checkpoints may not match the paper-scale
training configuration. Do not transfer a paper's score to a different checkpoint,
dataset, feature layer, or hardware environment.

Some model examples, including MERT's, load repository-supplied code using
`trust_remote_code=True`. Review that code, pin the model and dependency revisions, and
assess offline operation before running any candidate in the production worker.

### Longer-form descriptions and lyrics: exploratory leads

- [MusiLingo](https://github.com/zihaod/MusiLingo) combines MERT-330M with a
  Vicuna-based language model for captioning and music questions; its example setup
  uses a 7B language model. [LLark](https://proceedings.mlr.press/v235/gardner24a.html)
  is another published music-understanding approach with training code. These are
  research leads, not verified deployable Sidetrack models; check each component,
  checkpoint, dependency and data license.
- [Audio Flamingo 3](https://huggingface.co/nvidia/audio-flamingo-3) describes longer
  audio understanding, but its model card says **non-commercial research only** despite
  the paper's “fully open” wording. [Qwen2.5-Omni-3B](https://huggingface.co/Qwen/Qwen2.5-Omni-3B)
  is a smaller multimodal candidate with a separate research license. Neither has been
  evaluated for this library or on the rack. A 7B model's fp32 weights alone exceed
  8 GB; quantized or smaller alternatives still require compatibility, memory, latency
  and quality measurements.
- [LyricWhiz](https://github.com/zhuole1025/LyricWhiz) is a lyrics-transcription
  research lead, not a fully local drop-in: its documented method uses Whisper plus
  ChatGPT post-processing. Do not send private audio or transcripts to a remote service.
  Evaluate lyric errors, hallucinations, timing, language and silent/instrumental
  sections before displaying any result, and check rights to retain or share lyrics.
- A [pitch-correction detection paper](https://arxiv.org/abs/2403.05380) suggests
  another possible production-technique facet, but it does not establish accuracy on
  altered or heavily processed vocals in this library. A prediction would be a
  tentative description, never an artist-authenticity judgment.

### Interpretable audio facets

Useful candidates include beat/tempo, key and mode, integrated loudness and loudness
range, spectral centroid, energy in stated frequency bands, estimated vocal presence,
repetition and section boundaries. For example, [EBU R 128](https://tech.ebu.ch/docs/r/r128.pdf),
its [loudness-range supplement](https://tech.ebu.ch/docs/tech/tech3342.pdf) and
[Essentia's key extractor](https://essentia.upf.edu/reference/std_KeyExtractor.html)
define measurement methods. Their outputs are still affected by mastering, bitrate,
track length, resampling, tuning and arrangement. A 70/140 BPM pair can represent
half/double-time ambiguity, not two equally certain independent facts. A key estimate
may be inappropriate for atonal or highly processed music.

Additional facets worth evaluating are rhythmic regularity and syncopation, changes in
texture over time, vocal density, instrumental texture, harmonic changes and
stereo width. “Danceability” is a subjective construct, not an observable measure of
whether someone will dance, and a local estimate would not reproduce Spotify's
proprietary score. Spectral centroid is one proxy for brightness, not a complete
description of timbre. The existing embedding pipeline downmixes to mono, so stereo
width would require separately decoding suitable original audio and cannot be recovered
from the stored vector. Each facet needs its own definition, input/coverage and tests.

Display the method and version, actual input duration and whether it is a preview;
show ranges, alternatives or **unavailable** when warranted. A listener-relative
percentile can make brightness or bass easier to understand, but it is relative to the
specified listener, eligible tracks, time range and pipeline, not an objective universal
scale. Do not infer the singer's gender or a listener's identity from audio.

For structure, start with an honestly named **candidate boundary** or **high-intensity
segment**. The loudest bar after a boundary is not necessarily a drop. Detecting drops,
builds, breakdowns or vocal chops would need representative annotations and a dedicated
evaluation; the named classes are not supplied by All-In-One. Two exploratory leads are
[Drop Detector](https://github.com/felixmeyer6/drop-detector), which describes
audio-feature candidates and an XGBoost classifier, and
[Here Comes The Drop](https://github.com/hPerezz/here-comes-the-drop), which describes
feature-based markers and manual annotation. Their claimed performance, checkpoints,
licenses and compatibility have not been independently evaluated here; their playback
interfaces are not a recommendation to serve audio over HTTP.

### Text-to-audio labels and search

The joint text tower makes queries such as “melodic bass with airy vocals” plausible
without other listeners' labels. It does not make a cosine similarity a probability or
prove that a phrase correctly describes a track. The
[two-tower instrument study](https://arxiv.org/abs/2407.18058) finds substantial prompt
sensitivity and weak use of musical context; the
[COMET preprint](https://arxiv.org/abs/2605.29628) studies a more complicated
audio/text modality gap.

Comparing a term with its score distribution across one user's library, for example by
a per-term z-score, is a **candidate ranking heuristic**. It does not establish a
calibrated confidence or fix the modality gap; very low variance also makes the score
unstable. Compare raw cosine, library-relative ranking and other baselines on held-out
labels; vary prompt wording, include close confusions and hard negatives, allow
abstention, and show representative tracks. Curate vocabulary for the actual library
instead of assuming a fixed electronic-genre list is complete or universally correct.

### Neighbours, recommendations and “why”

The [2026 comparison of nine audio representations](https://arxiv.org/abs/2604.23077)
finds that success on conventional MIR tasks does not automatically transfer to
recommendation. A separate [2026 preprint](https://arxiv.org/abs/2608.06928) finds
that the value of pretrained audio representations depends on how the recommendation
system uses them, and includes content-free controls. Neither result proves performance
for this listener.

Candidate approaches, in increasing complexity:

1. Return actual nearest neighbours in the accepted embedding space; explain that they
   are close according to this model, not necessarily *why* they sound alike.
2. Score against several recent and long-term listening examples, rather than assuming
   one average vector represents every taste. Compare equal-track and play-weighted
   profiles, and offer a way to filter repeats, previews and excluded sessions.
3. Rerank for diversity or explicitly let a listener choose “closer” versus “more
   exploratory”; compare with a simple recent/frequent baseline and a random control.
4. For a club, suggest tracks near two opted-in libraries, but surface which members have
   enough linked audio and let each person review the suggestions.

[Maximal marginal relevance](https://doi.org/10.1145/290941.291025) is one concrete
reranking candidate: greedily balance closeness to the query against redundancy with
already selected results. It does not guarantee a better playlist or good musical
transitions. Test it against unmodified nearest neighbours, let the listener control
the tradeoff, and avoid suppressing a genuinely preferred sound merely for variety.

A genuine “these two tracks share the section at 1:02” feature needs newly computed,
timestamped section/window representations and an alignment evaluation. The current
pooled vectors cannot support that explanation, and the 180-second cap can omit later
sections. Do not turn a high audio-similarity score into a recording-identity assertion.

### Listening eras and richer emotional language

For a listening journey, compare eligible listening windows using actual track or
play-weighted summaries and surface the tracks behind any proposed shift. Offline
change-point tools such as [ruptures](https://github.com/deepcharles/ruptures) offer
candidate search methods and cost functions; the choice determines what kind of change
is sought. Compare against a simple rolling-window baseline and test stability under
coverage gaps, repeat plays and reasonable parameter changes. An algorithmic boundary
is not a life event, and a missing period is not a zero-valued period.

The [Geneva Emotional Music Scale research](https://pubmed.ncbi.nlm.nih.gov/18729581/)
offers a richer vocabulary than two valence/arousal axes and found differences between
felt and perceived emotion. It is a possible source of self-report questions or
descriptive hypotheses, not a way to infer the listener's feelings from an audio
embedding. Any proposed categories need separate labels, evaluation and permission to
use the instrument.

## 3. Evaluation data and rights

| Source | Useful for | Important restrictions or gaps |
| --- | --- | --- |
| [DEAM](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0173392) | Static and time-varying human ratings of perceived valence and arousal; 1,802 recordings/excerpts, including 58 full songs and 1,744 45-second excerpts. | Human annotations are crowdsourced or lab-collected. The article and individual audio/annotation artifacts do not necessarily share identical terms; confirm the actual files' rights. The original data site was inaccessible during review. |
| [MusAV](https://github.com/MTG/musav-dataset) | Relative judgments: which of two clips sounds more arousing or positive, with several annotator-agreement subsets. Useful for testing ranking rather than just absolute scores. | Its AV annotation metadata is CC BY-NC-SA 4.0. Its Spotify previews and API metadata are available on request for non-commercial scientific research only; this is not blanket permission for product use. |
| [MTG-Jamendo](https://github.com/MTG/mtg-jamendo-dataset) | Genre, instrument and mood/theme tagging; the published splits have 55,525 tracks and 87/40/56 tags respectively. | Tags are uploader-supplied. Its low-quality mood subset is about 46 GB and full low-quality audio about 156 GB: both exceed the project's 40 GB **SSD budget**, though the rack also has HDD. Check each audio license and plan storage before use. |
| [PMEmo](https://github.com/HuiZhangDB/PMEmo) | 794 popular songs with human affect annotations, chorus clips and physiological signals; a possible cross-dataset check. | Popular-song/chorus bias is unlike the owner's collection. Verify specific audio, annotation and redistribution terms; physiology is not a diagnosis. |
| [MusicCaps](https://huggingface.co/datasets/google/MusicCaps) | 5,521 musician-written descriptions of 10-second clips; useful for studying descriptive prompts and retrieval. | Its card lists CC BY-SA 4.0 for the dataset, not automatic permission for the referenced YouTube audio. Do not schedule or automate yt-dlp to obtain it. |
| [Song Describer](https://github.com/mulab-mir/song-describer-dataset) | About 1,100 human-written captions for 706 recordings, with approximately two minutes of audio per track; useful for caption and text-retrieval evaluation at a different duration from MusicCaps. | Repository code is MIT and the dataset is CC BY-SA 4.0. The recordings have their own Creative Commons licenses; check individual terms and genre coverage. Captions are human annotations, not labels for the owner's tracks. |
| [MuChoMusic](https://github.com/mulab-mir/muchomusic) | Multiple-choice evaluation of music understanding by audio-language models. | The repository says MIT code and CC BY-SA 4.0 dataset; check the underlying audio sources and rights separately. A benchmark score is not a guarantee of correct free-text descriptions. |
| [Jam-ALT](https://huggingface.co/datasets/jamendolyrics/jam-alt) | A 79-song, four-language benchmark for lyrics transcription, including readability and line-level timing. | It is not word-aligned, and its small test set cannot establish performance on every genre or language. Check the lyrics and each recording's actual license before storage, display or redistribution. |
| [Harmonix Set](https://github.com/urinieto/harmonixset) | Beat, downbeat and functional-section annotations for 912 Western pop tracks. | It is not a representative EDM-drop dataset. Spectrograms have their own license agreement; YouTube references do not imply audio download rights. |

The local mood-probe branch (`origin/feat/mood-probe-benchmark`,
`docs/AUDIO-BENCHMARK.md`, run `20261031-204732-9b07ff0`) reports five repeats of
nested five-fold validation on DEAM: MuQ-MuLan valence R² **0.615** and arousal R²
**0.688**. Artist metadata was unavailable, so the splits were **not artist-grouped**
and may flatter absolute scores. Human ratings correlate at 0.57, held-out predictions
at 0.83, and predictions on the owner's 233 tracks at 0.91. This diagonal is a warning
about distinction between axes, not proof of a specific worst-performing quadrant. The
owner's listening check and decision were pending.

The [MARBLE benchmark](https://arxiv.org/abs/2306.10548) and other published results
provide research context, not a direct numerical comparison with this run: datasets,
subsets, preprocessing and splits may differ. DEAM and earlier MediaEval/EmoMusic data
are related; the exact file overlap and split compatibility were not established here.
Check IDs, audio duplicates and artist/recording groups before combining datasets.

### A practical validation protocol

Before any result becomes a user-facing claim:

1. **Freeze the task and population.** Record model and checkpoint revisions, audio
   coverage, preview/full source, preprocessing, time range, label vocabulary, and a
   held-out set of obscurer tracks, electronic styles and altered versions. Avoid
   leaking a track, its alternate upload, or its artist across splits where feasible.
2. **Use task-specific labels.** For neighbours and discovery, use blind pairwise
   listener judgments and precision/ranking measures; separate “same recording” from
   “sounds similar.” For text, include prompt variants and hard negatives. For mood,
   compare both axes, relative rankings and calibration to simple baselines, with
   artist-grouped evaluation when metadata permits. For beats and sections, use
   timestamp tolerances and report both boundary and label accuracy.
3. **Report coverage and failure.** Show missing audio, uncertain links, disagreement,
   unknown categories, short files, model failures and the fraction excluded. No
   fabricated tags, interpolated missing weeks, or confidence values derived merely
   from similarity scores.
4. **Test robustness.** Compare full tracks with previews, loudness-normalized and
   original audio where appropriate, genre/artist groups, clustering seeds and
   vocabulary versions. Check whether results change materially under small input or
   corpus changes. Report uncertainty appropriate to the sampling unit, not just
   repeated plays of the same recording.
5. **Keep the human gate.** Provide examples and a way to reject or correct results.
   The pending owner listening check is part of the mood gate, not a formality to
   substitute with the DEAM R² scores.

## 4. User jobs and presentation directions

| User question | Proposed experience | Required honesty or dependency |
| --- | --- | --- |
| “What else in my library sounds like this?” | A neighbour list, artist/album exploration, and optional textual search. | Existing vectors cover assets, not every listen; links and search integration are needed. Similarity is model-relative. |
| “What does this obscure track sound like?” | A track card with mood estimates, tempo alternatives, key, brightness, bass, vocal presence and representative neighbours. | Each facet has its own model, provenance and available/not-computed/failed state. Do not imply the description comes from a community consensus. |
| “How did my listening change?” | A weekly/monthly timeline, listening clock, theme river and eras, with drilling into the underlying tracks. | Show plays with usable audio, denominators, timezone, baseline and excluded/missing data. A change-point is a hypothesis, not a life event. |
| “What did I love and forget?” | Resurface past favourites and repeat patterns using the user's own history. | Historical import and coverage determine what “forgotten” can mean; no fabricated loves or missing-year estimates. |
| “Find a path between two moods or sounds.” | A user-directed sequence or bridge list, with options for closeness, novelty and repetitions. | Evaluate the actual sequence; smooth embedding distance is not a guarantee of musical transitions. A playlist of metadata must not become an HTTP audio service. |
| “What do we both enjoy?” | Opt-in side-by-side overlap, distinct tastes and a few bridge-track nominations. | Each participant controls access and deletion; unequal audio coverage and differing activity levels are visible. Sound overlap is not personality or interpersonal compatibility. |
| “Do I choose different music when I feel different?” | An optional private check-in and an exploratory association view. | Perceived emotion of music is not the listener's mood. Show the definition, timing, n and uncertainty; never diagnose or imply causality. |
| “Can I share my year or a cool track?” | An explicit shareable receipt, poster, one-track story, or year-in-music card. | Preview exactly what leaves the private account, including tracks, counts and any check-in data. Sharing is opt-in and revocable where possible. |

**Self-report and autoplay cautions.** A threshold of eight weeks in a draft proposal is
a product rule, not evidence that a correlation or its interval is reliable. Define
same-week versus lagged comparisons, handle ties and constant values, missing data,
repeated observations, autocorrelation and selection bias. A bootstrap interval is
not automatically valid for dependent weekly observations, and no fixed number of
future check-ins guarantees a narrower interval. Check-ins are sensitive personal
information: keep them private and optional, with deletion and no clinical claims.

Similarly, a long late-night listening session may be autoplay, intentional listening,
or something else. A flag is a heuristic, not evidence of sleep or intent. Let users
review and correct it, and disclose whether flagged sessions are excluded. The
[population study of listening across time](https://research.atspotify.com/publications/global-music-streaming-data-reveals-robust-diurnal-and-seasonal-patterns-of-affective-preference)
is useful for questions to explore; it cannot establish an individual's mood or cause.

### Visual vocabulary and accessibility

- A **theme river** can show changes in play-weighted theme shares over time; the
  original [ThemeRiver](https://www.pnnl.gov/publications/themeriver-visualizing-thematic-changes-document-collections)
  illustrates the temporal metaphor. Label bands, show exact values in an accessible
  table, and leave weeks with insufficient data as gaps rather than interpolation.
- A **taste galaxy** is an exploratory 2-D projection, not the original 512-dimensional
  geometry. [UMAP's FAQ](https://umap-learn.readthedocs.io/en/latest/faq.html) warns
  that density is not well preserved; [t-SNE examples](https://distill.pub/2016/misread-tsne/)
  illustrate how maps can mislead. Recompute real neighbour lists in the original
  vector space, give a list alternative, and do not claim that islands or visual
  distances establish real categories.
- Use text, patterns and shapes as well as color, offer keyboard and screen-reader
  alternatives, respect reduced motion, and provide high-contrast readable text.
  [WCAG 2.2 use-of-color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
  explicitly disallows color as the only way to distinguish information.
- Treat the mockups as illustrated concepts. Users should see **no audio**, **not
  computed**, **uncertain link**, **insufficient sample**, **stale model**, or **failed
  analysis** as distinct states, rather than a plausible-looking default.

## 5. Product survey: what to borrow, and what not to assume

This section preserves the completed agent's product report plus useful verified leads
from the interrupted UX research. Features and policies are time-sensitive.

| Product or source | Useful observation | Sidetrack implication |
| --- | --- | --- |
| [stats.fm](https://stats.fm/) | Top lists and lifetime-history import are central to its pitch. | Make imported-history completeness and the time window visible; do not pretend a short import is lifetime history. |
| [ListenBrainz Year in Music](https://blog.metabrainz.org/2026/01/02/year-in-music-2025-new-and-improved/) and [Last.fm weekly charts](https://www.last.fm/charts/weekly) | Recaps, historical exploration and week-by-week listening can be recurring rather than a once-yearly novelty. | Let users browse past periods and drill down to actual listens; no crowdsourced track tags are needed for play counts. |
| [Apple Music Replay](https://support.apple.com/en-us/109356) | Its help page distinguishes play counts and time listened, with monthly and yearly views and an eligibility state. | Label the unit and denominator, offer useful empty states, and do not silently substitute plays for minutes. |
| [YouTube Music Recap 2024](https://blog.youtube/news-and-events/2024-music-recap-youtube/) | Animated cards and a listening timeline package data as a story; it also uses fictionalized character labels. | Borrow the timeline and shareable presentation, not claims about a person's personality. |
| [Receiptify](https://receiptify.herokuapp.com/about.html) | A compact, screenshot-friendly receipt; its FAQ explains that the “amount” field means different things for different categories and that upstream top rankings are not fully explained. | Put units and ranking source directly on a share card instead of relying on the metaphor to explain them. |
| [Instafest](https://www.instafest.app/) | Turns top artists into a festival-style lineup. | A personal festival poster could be playful when its source, period and selection rules are explicit. |
| [MusicTaste.Space](https://musictaste.space/) | Hand-arranged album art, a daily track with a reason, and a single compatibility percentage. | Let people tell a story and nominate a bridge track; avoid presenting one percentage as a verdict on two people. |
| [Plexamp sonic analysis](https://www.plex.tv/blog/super-sonic-get-closer-to-your-music-in-plexamp/) | The vendor describes audio-based similarity, track/album radios and historical mixes, including music with little metadata. | A strong precedent for locally analyzed obscure music; its product claims do not validate Sidetrack's model or permissions. |
| [Cyanite model outputs](https://docs.cyanite.ai/docs/concepts/model-outputs/) | The vendor documents versioned outputs, separate per-facet scores and segment-level values. | Version each facet and distinguish segment results from track summaries. This is design inspiration, not a recommendation to upload private audio. |
| [Skiley](https://skiley.net/) | Vendor claims include BPM/key sorting and playlist-management tools. | Facets are most useful as filters and sorting controls, with ambiguity and confidence visible. Independent quality was not established. |
| [Every Noise](https://everynoise.com/) and [its creator's interview](https://hmc.chartmetric.com/glenn-mcdonald-spotify-you-have-not-yet-heard-your-favorite-song/) | Navigable genre maps can make exploration fun; genre also reflects community and audience. | Provide a navigable map or list, but label model-generated terms as suggestions rather than definitive cultural taxonomy. |
| [Music Galaxy](https://cprimozic.net/blog/building-embedding-visualizations-from-user-profiles/) | An exploratory artist galaxy built from listener co-occurrence/similarity, not audio embeddings. | Borrow the interaction, not its data assumptions; Sidetrack's own map would be audio-derived and still projection-distorted. |
| [Discogs collection help, archived 2022](https://web.archive.org/web/20220830222427/https://support.discogs.com/hc/en-us/articles/360007331534) | Its value estimate describes its sales-history basis and excludes releases without sales. This is a historical page, not a current guarantee. | Report missing coverage and explain estimate boundaries rather than guessing. |
| [The Pudding's satirical critic](https://pudding.cool/2020/12/judge-my-spotify/) | It explicitly discloses a faux AI and a joke database. | Playful writing is fine when labelled; do not dress invented personality judgments as analysis. |

**Unverified leads:** Obscurify's page returned 429; Volt.fm returned 403 or rotating
content; MusicScape's client-rendered page exposed no readable feature description.
Their detailed feature claims, current operation and access status were not established.
Historical third-party descriptions of Chosic's mood filters are leads, not proof its
current Spotify integration works. Spotify's
[November 2024 announcement](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
restricted Audio Features, Audio Analysis, recommendations and related artists for new
use cases while describing an exception for existing extended-mode access. It does not
prove whether any named third-party app currently works or broke.

## 6. Follow-ups for the existing proposals

The seven OpenSpec changes are drafts; these findings have not silently rewritten their
accepted-looking design choices. Reconcile the following before applying them:

1. **`import-listenbrainz-history`:** make inferred autoplay reviewable and reversible;
   distinguish “unclassified” from deliberate listening. Define timezone and
   missing-history behavior, import provenance and safe retry semantics.
2. **`resolve-listens-to-audio`:** exact-looking normalized artist/title matches can
   still conflate versions. Preserve source evidence, expose ambiguity and manual
   correction, and do not equate sonic similarity with recording identity.
3. **`add-track-mood-scores`:** require the owner listening gate and evaluate
   out-of-domain tracks. Calculate percentiles for the requesting user's eligible
   library, not as one global percentile stored on a shared asset. Record the reference
   population, model/probe revision and coverage.
4. **`add-sound-themes`:** remove the unsupported claim that per-term z-scores correct
   the modality gap. Treat clustering algorithm, noise threshold and fallback as
   hypotheses; evaluate stability, vocabulary bias, abstention and user renames across
   library/model updates.
5. **`add-weekly-listening-profile`:** make each metric's denominator, time zone and
   inclusion rules explicit. Revisit the eight-week correlation threshold and the
   proposed bootstrap for temporally dependent data; protect, export and delete
   check-ins separately from ordinary public listening visibility.
6. **`add-listening-visuals`:** make projection distortion explicit, use original-space
   neighbours, preserve missing-data gaps and provide accessible non-color/list views.
7. **`add-sound-compatibility`:** define per-user sample and coverage, calibration and
   consent/revocation. Do not label an unvalidated cosine-derived number “moderate”
   compatibility or expose private history and derived data after consent is withdrawn.

Additional ideas such as a per-track facet card, text search, version discovery, a
listening journey and timestamped “why” explanations are research directions, not
approved implementations. Each needs its own scoped proposal and task-specific
evaluation before changing production behavior.
