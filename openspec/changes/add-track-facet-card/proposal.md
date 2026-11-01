# Proposal

## Why

About half the owner's tracks are unknown to AcoustID/MusicBrainz, so "what does this obscure
track sound like?" cannot be answered from community tags, and Spotify's audio features are
unavailable to this app (ADR 0003). The stored MuQ-MuLan vector supports neighbours, but it
cannot say a track is around 140 BPM, quiet, bright or bass-heavy. Interpretable, measured
facets (mockup 6 in docs/research/MOCKUPS.md) give a track card that people can check
against their ears, as long as every number carries its method, input and uncertainty.

## What Changes

- **A facet benchmark in audio-lab first.** `audio-lab facets` runs candidate methods for
  each facet over a manifest on the rack (GTX 1070, CPU), records outputs, cost and license
  facts, and scores them against reference annotations where rights allow. Nothing reaches
  production until a facet has a recorded run, a passed license review and the owner's
  decision (the ADR 0004 pattern).
- **Facets, per audio asset, each versioned.** Tempo with half/double-time alternatives and
  beat timestamps (Beat This! is the lead candidate); key and mode with an estimate strength,
  allowed to be `unavailable` for atonal or weakly tonal audio; EBU R 128 integrated loudness
  and loudness range; spectral-centroid brightness; energy share in stated frequency bands
  (bass); estimated vocal presence; candidate section boundaries and high-intensity segments.
  Every facet records method, method version, analyzed duration, preview/full and a state:
  `available`, `not_computed`, `failed` or `unavailable`.
- **Operator-started facet jobs** with the same backfill, idempotency and per-asset failure
  rules as embeddings. Neural methods run on the `gpu` queue; signal-processing methods on
  the CPU worker.
- **Listener-relative percentiles at read time**, computed over the requesting user's
  eligible library (tracks in their included plays whose audio link resolves unambiguously to an
  asset with that facet available under the same method version), reporting the reference size, with an insufficient-sample
  state. No global percentile is stored on a shared asset.
- **A read route and a facet panel on `/tracks/{id}`** that render stored values only, show
  each facet's method, analyzed duration and state, and use restricted wording: "candidate
  boundary", never "drop"; no danceability; no singer gender.

Out of scope:
- Mood estimates (`add-track-mood-scores`), text tags or search, sound themes, neighbours on
  the card (they need their own route), and section-level "why" explanations
  (`add-timestamped-audio-windows`).
- Drop, build, breakdown or vocal-chop labels: no evaluated source supplies them (All-In-One
  has no drop class). A danceability score, singer gender or any identity inference.
- Stereo width and other facets that need non-mono decoding beyond loudness; rhythmic
  regularity, syncopation and texture-change facets (later proposals after this benchmark).
- Essentia library or MTG model heads unless the licensor clarifies the conflicting model
  terms and the AGPL implications are accepted in a new ADR; madmom models (CC BY-NC-SA)
  unless the license review accepts them.
- Playing or serving audio, scheduling acquisition, or uploading audio to external services.
- New infrastructure: results live in Postgres and run on the existing job queues.

## Capabilities

### New Capabilities
- `analysis/audio-facets`: how interpretable per-asset audio facets are computed, versioned,
  stored with their state and input coverage, and turned into listener-relative percentiles.
- `web/track-facets`: how the track page and its API route present facets, their provenance,
  their distinct missing states and restricted wording.

### Modified Capabilities
- `analysis/audio-benchmark`: adds facet runs (candidate methods, cost, license records and
  reference scoring) to the audio lab. Existing embedding-benchmark requirements are unchanged.

## Impact

Current state:
- **Observed:** nothing computes tempo, key, loudness or other facets. The legacy
  `track_features` table holds Spotify-shaped columns (`energy`, `valence`, `danceability`,
  `tempo`, ...) keyed by track (`sidetrack/analysis/models.py`), fed by an `analysis:write`
  route no client holds (`sidetrack/analysis/routes/tracks.py`); docs/status.yaml lists
  Spotify audio features as broken and taste profiles as a stub.
- **Observed:** the embedding pipeline decodes to mono, cuts 10 s windows and caps full tracks
  at 180 s (`sidetrack/analysis/embeddings/audio.py`, `registry.py`). Facets that need the
  whole track or both channels (loudness) cannot reuse that decode unchanged.
- **Observed:** audio-lab adapters cover embedding models only (MuQ, MuQ-MuLan, MERT-95M,
  CLAP: `services/audio-lab/src/audio_lab/adapters/models.py`); PyTorch lives only in
  audio-lab and `services/gpu-worker` (ADR 0004, ADR 0010).
- **Observed:** production holds 862 assets with files on docker-0's HDD
  (`/srv/sidetrack/audio`, ADR 0010); no HTTP route uses analysis results yet (docs/STATUS.md).
- **Assumed:** Beat This! runs on Pascal in fp32 within the 8 GB card alongside nothing else;
  task 2.3 measures it. If it does not, tempo runs on CPU or remains `unavailable`.
- **Assumed:** facet rows for 862 assets are a few MiB including beat timestamps; task 4.4
  measures the real size against the ~40 GB SSD budget (ADR 0005).

Affected:
- `services/audio-lab` (facet adapters, `facets` command, report), its `uv.lock`.
- `sidetrack/analysis/facets/` (new), `sidetrack/audio.py` (`facets` subcommand), job runner,
  `migrations/` (next free number), `services/gpu-worker` dependencies if a neural method is
  accepted, root extras only for CPU-only libraries that pass license review.
- API route and `packages/api-client`; `apps/web` track page.
- Docs: docs/AUDIO-FACETS.md (new), docs/AUDIO-BENCHMARK.md, docs/MODULES.md,
  docs/status.yaml, a new ADR for accepted facet methods.

Dependencies:
- `resolve-listens-to-audio` (audio-for-track and per-user eligible library), and through it
  `import-listenbrainz-history`. Facet computation itself depends only on assets.
- `add-listening-visuals` owns the `/tracks/{id}` page shell; this change adds the facet panel
  (or creates a page with only that panel if the shell has not landed).
