# Proposal

## Why

The first benchmark (run `20261026-223453-0ec1bac`, recorded in `docs/AUDIO-BENCHMARK.md`) narrowed the field to MuQ (duel win rate 0.65) and MuQ-MuLan (0.61), but it can't pick between them.

Observed problems with its data:
- **Narrow:** the seeds came from a 4-month ListenBrainz snippet (July–October 2026, 3,084 listens). It was almost one genre, melodic bass and future bass.
- **Dirty:** it included two podcast episodes ("The Best in Jest", about 55 minutes each). It also mixed sleep and ambient tracks in with no label.
- **Too few labels:** the only objective tests were preview→full recall and same-artist rate. Neither says whether a model's neighbours match the owner's taste or separate genres.

The owner has now supplied the full ListenBrainz export: 74,826 listens from 2019 to 2026, 22,174 tracks and 8,970 artists. 70% of listens carry a YouTube link and 74% are MusicBrainz-mapped, which makes a cleaner and broader benchmark possible.

## What Changes

- **Personal seed builder (`audio-lab seeds`):** reads a ListenBrainz export, which stays outside the repo, and writes `seeds.csv` (the acquisition seed format), `labels.csv` and `colisten.csv`. It:
  - drops non-music: listens over 10 minutes, known podcast and series titles, and the "A YouTube Labs experiment" pseudo-artist
  - resolves uploader-channel listens to their real artist and title. Observed: 6,136 unmapped listens are titled "Artist - Title" under channels such as AirwaveMusicTV, WaveMusic and MrSuicideSheep.
  - labels sleep tracks from long late-night autoplay sessions, which are also excluded from co-listening
  - stratifies picks across years (2020–2026) and play-count bands, with at most 2 tracks per artist
  - deliberately includes both tracks of strongly co-listened pairs, so the co-listening test has positives in the pool
- **Genre control set (`audio-lab control-seeds`):** writes seeds and genre labels for about 10 tracks from each of about 15 Deezer public genre charts (`/genre`, `/chart/{id}/tracks`). Their audio is fetched by the existing `python -m sidetrack.audio fetch`.
- **New automatic metrics in `audio-lab report`**, from the optional `labels.csv` and `colisten.csv`:
  - **genre precision@10** on the control set
  - **co-listening hit rate**
  - **sleep-cluster purity**
- **Duels limited to chosen models:** `audio-lab report --duel-model muq --duel-model muq-mulan` puts every duel on the pair that is still undecided.
- **Pass gate v2** in `docs/AUDIO-BENCHMARK.md`.
- **Close out the first benchmark:** archive `add-audio-lab-benchmark` with its result recorded as "MuQ leads provisionally; the final pick is deferred to v2".

## Capabilities

### New Capabilities
- `analysis/benchmark-seeds`: how benchmark seed lists and their labels are built from the owner's listening history and from public genre charts. This includes cleaning, stratification, labels and co-listening pairs, and keeping personal data out of the repo.

### Modified Capabilities
- `analysis/audio-benchmark`: adds labelled metrics (genre precision, co-listening, sleep purity) and duels restricted to chosen models. This capability is created when `add-audio-lab-benchmark` is archived, which this change requires first.

## Out of scope

- **Database or acquisition changes.** Labels and co-listening pairs live in files next to the manifest. `sidetrack.analysis.audio` and the `audio_assets` table are unchanged.
- **Google Takeout or YT Music history parsing.** ListenBrainz already records YT Music plays (5,988 listens) and Pano Scrobbler. Takeout liked songs can be a follow-up.
- **Last.fm import.** Its history already reached ListenBrainz through the importer (5,065 listens).
- **Integrating a model into Sidetrack** (pgvector, `gpu` queue). That waits for the v2 decision.
- **Re-running the GTX 1070 Ti timing.** It stays a separate follow-up.

## Impact

- **Code:** `services/audio-lab`. New `seeds.py`, `control.py` and `labels.py`, with additions to `metrics.py`, `duels.py`, `report/` and `cli.py`. The control-set builder calls the public Deezer API over HTTPS, read-only, with no key.
- **Data:** the owner's export, seeds, labels and pairs live under `E:/sidetrack/benchmark-v2/`, never in the repo. Tests use small synthetic exports.
- **Docs:** `docs/AUDIO-BENCHMARK.md` (gate v2, results), `services/audio-lab/README.md`, `docs/status.yaml`.
- **Storage:** about 400 seeds × (full + preview) is about 8 GB on the E: HDD, within the ADR 0005 HDD budget.
