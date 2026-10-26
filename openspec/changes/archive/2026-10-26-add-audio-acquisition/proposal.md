# Proposal

## Why

Audio-first analysis is the point of the rework, and the ADR 0004 benchmark needs about 100 real tracks, including obscure ones, before any model can be judged. Observed: Sidetrack has no audio. `data/audio/` is empty, there's no audio table, and Spotify previews are unavailable (ADR 0003). ADR 0007 already chose how to get audio: an explicit, personal yt-dlp command plus Deezer previews, with every file fingerprint-checked and recorded. This change builds that command so the benchmark has audio to run on.

## What Changes

- **New opt-in CLI** `python -m sidetrack.audio fetch` takes a seed list (CSV of artist, title and optional YouTube video ID or Deezer track ID) and fetches each track:
  - **Full track** from YouTube Music via yt-dlp: the native best-audio stream, not transcoded. A cookie file is optional and passed by path.
  - **30-second preview** from Deezer's public search API, downloaded right away because the preview URLs expire.
- **Content-addressed storage:** files are written as `<SIDETRACK_AUDIO_DIR>/<sha256>.<ext>`, meant for the HDD. The same bytes are stored once.
- **Verification:** each file is fingerprinted with Chromaprint (`fpcalc`) and looked up on AcoustID. The asset records whether the match confirms the requested artist and title, contradicts it, or can't tell.
- **New analysis-owned table `audio_assets`** (migration `0009_audio_assets`) holds hash, path, source, source ID, kind (full/preview), format, duration, verification result, fetch time, and optionally the catalog track. Catalog tracks are resolved through catalog's public `resolve_listen_track`. A seed that MusicBrainz can't resolve is still fetched, with its requested artist and title kept on the asset.
- **`python -m sidetrack.audio manifest`** exports the stored assets as a CSV for the audio lab (`add-audio-lab-benchmark`), which never reads the database.
- **`python -m sidetrack.audio prune`** deletes files under a retention setting and keeps the asset rows. ADR 0007 says derived features outlive files.
- **Guardrails from ADR 0007:**
  - Fetching runs only when `SIDETRACK_AUDIO_FETCH_ENABLED=true` and someone types the command.
  - Nothing registers it as a job or schedule.
  - No API route or web page serves audio or exposes file paths.
  - Cookie paths and contents never appear in logs or rows.
- **New optional dependency extra** `audio`: yt-dlp and pyacoustid. `fpcalc` is a system binary and is checked at startup. The extra isn't in the API, worker or web images.

## Capabilities

### New Capabilities
- `analysis/audio-assets`: how audio is acquired on explicit request, stored by content hash, verified, recorded, exported and pruned, and the guarantees that it is never scheduled or served.

### Modified Capabilities
None.

## Out of scope

- **The benchmark itself:** models, embeddings and reports. That's `add-audio-lab-benchmark`.
- **Owned-file import from a beets library:** ADR 0007 allows it, but the owner chose yt-dlp and Deezer for now. The source enum leaves room for it.
- **Automatic acquisition:** no fetching for listens or nominations. ADR 0007 forbids scheduling.
- **The MusicBrainz mirror (ADR 0005):** catalog resolution keeps using the rate-limited web API, about 2 minutes per 100 seeds.
- **Deploying fetch on the rack:** it runs on the owner's machine against the configured database and audio directory.

## Impact

- **Code:**
  - new `sidetrack/analysis/audio/` with `AudioAsset` (analysis models), the fetchers, fingerprint verification and the public functions
  - the composition CLI `sidetrack/audio.py`
  - migration `migrations/versions/0009_audio_assets.py`
- **Config:** `SIDETRACK_AUDIO_DIR`, `SIDETRACK_AUDIO_FETCH_ENABLED`, `ACOUSTID_API_KEY` and `SIDETRACK_AUDIO_RETENTION_DAYS`, documented in `config/ENVIRONMENT.md` and `.env.example`. The AcoustID key is a free registration the owner does.
- **Dependencies:** an `audio` extra in the root `pyproject.toml` and `uv.lock`. Both packages are light; no PyTorch. System `fpcalc`.
- **Docs:** `docs/MODULES.md` (audio_assets is owned by analysis), `docs/status.yaml` (a new "Audio acquisition" capability), and AGENTS.md hard rules unchanged.
- **Legal and terms:** ADR 0007 already records that downloading from YouTube breaks its terms and that the owner accepted this for personal use. Deezer previews are subject to Deezer's API terms. Nothing is redistributed.
