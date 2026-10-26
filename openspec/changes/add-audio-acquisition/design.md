# Design

## Context

See proposal.md for motivation, and the `analysis/audio-assets` spec for required behaviour. Constraints:

- **ADR 0007** fixes the shape: an explicit CLI, `audio/<sha256>.<ext>` on HDD, Chromaprint/AcoustID confirmation, an analysis-owned asset table, and no HTTP serving.
- **ADR 0001 module rules:** analysis owns `audio_assets`. Catalog rows are created only through `sidetrack.catalog.resolve_listen_track`. Import contracts in `pyproject.toml` enforce both.
- **Dependency policy:** root `pyproject.toml` forbids heavy dependencies (`pyproject.toml:6-9`). yt-dlp and pyacoustid are pure Python and small. PyTorch stays out; it belongs to the audio lab.
- **Hardware:** the owner runs this on their Windows PC with the database URL and an HDD path. `fpcalc` must be on PATH; Windows and Linux builds are published by the Chromaprint project.

## Goals / Non-Goals

**Goals:**
- Fetch about 100 seeds in one unattended run, and rerun safely: content hashing makes reruns idempotent.
- Make every wrong download visible through verification, not silent.
- Give the audio lab a file-only manifest, so it needs no database driver.

**Non-Goals:**
- Parallel downloading. Sequential is enough for 100 seeds and kinder to both services.
- Transcoding or loudness normalisation. The lab resamples per model.
- Matching against the MusicBrainz mirror (ADR 0005).

## Decisions

### 1. Composition CLI over a domain-public API

`sidetrack/audio.py` (run as `python -m sidetrack.audio fetch|manifest|prune`) parses arguments and settings, then calls the public functions of `sidetrack.analysis.audio`: `fetch_seed`, `export_manifest`, `prune_assets` and `read_seeds`. This mirrors `sidetrack/club_admin.py`. The package has four modules:
- `sources.py`: the YouTube Music and Deezer fetchers behind one small protocol
- `store.py`: hashing and writing files
- `verify.py`: fpcalc and AcoustID
- `assets.py`: rows and the public functions

A protected import-linter contract allows only the package itself and `sidetrack.audio` to import `sidetrack.analysis.audio`, so the API, worker, job runner and queue modules can't reach the fetch code. The package isn't re-exported from `sidetrack.analysis`, which the job runner imports. yt-dlp and pyacoustid are imported lazily inside the source and verifier classes, so images without the `audio` extra still import the analysis package.

Seed CSVs may carry an optional `album` column. Without it, `resolve_listen_track` can only link a track already in the catalog, because creating a track needs an album.

Alternative considered: a Procrastinate task on the `gpu` or `default` queue. Rejected, because ADR 0007 forbids scheduling and a queue task invites it.

### 2. Sources

- **YouTube Music:** yt-dlp's Python API with `format=bestaudio`, no postprocessors, downloading to a temporary file in the audio directory. It searches `https://music.youtube.com/search?q=<artist> <title>#songs` and takes the first song result, unless the seed gives a video ID. `cookiefile` comes from `--cookies PATH` and is never echoed. yt-dlp's logger goes through a filter that drops lines containing the cookie path.
- **Deezer:** `GET https://api.deezer.com/search?q=artist:"<artist>" track:"<title>"` using the existing `httpx`. It takes the first result with a `preview` URL, unless the seed gives a Deezer ID (`GET /track/<id>`), and downloads the MP3 straight away.
- **Rate:** one request per second per source. After a full download, each source waits a short delay before the next seed.

### 3. Storage

The file is streamed to `<dir>/.partial-<uuid>` while hashing. On completion it's renamed to `<sha256>.<ext>`, where the extension comes from the container yt-dlp reports, or `mp3` for Deezer. If that hash already exists, the partial file is discarded and the existing row is reused. The asset path is stored relative to `SIDETRACK_AUDIO_DIR`, so the directory can move between drives.

### 4. Verification

`pyacoustid.fingerprint_file` (wrapping `fpcalc`) is looked up with `meta=recordings`. The asset is:
- **`confirmed`** when the top result's score is at least 0.8 and its artist and title match the seed after normalisation (casefold, strip punctuation and "feat." clauses, title similarity of at least 0.85)
- **`mismatch`** when the score is at least 0.8 and they don't match
- **`unverified`** otherwise, or when there's no key or the lookup fails

Previews often fingerprint poorly. Their Deezer ID was chosen by metadata, so `unverified` previews are expected and reported separately in the summary.

### 5. Table

`audio_assets` columns:
- `id` uuid, primary key
- `sha256` char(64), unique
- `track_id` uuid, nullable, foreign key to `tracks`, ON DELETE SET NULL
- `seed_artist` and `seed_title` text
- `source`: enum `audio_source` (`youtube_music`, `deezer_preview`)
- `source_ref` text
- `kind`: enum `audio_kind` (`full`, `preview`)
- `path` text, `format` text, `duration_s` float
- `verification`: enum `audio_verification` (`confirmed`, `mismatch`, `unverified`)
- `acoustid_score` float, `recording_mbid` text
- `fetched_at` and `file_deleted_at` timestamptz

There's a unique index on (`source`, `source_ref`). Migration `0009_audio_assets` follows `0008_per_user_authorization`. `test_migrations.py` covers drift.

### 6. Testing without the network

Sources and the AcoustID client are injected. Tests use doubles under `tests/` that return fixed bytes, IDs and match payloads. CI never touches YouTube, Deezer or AcoustID. One manual smoke run with real sources is a task, not a CI test.

## Risks / Trade-offs

- [yt-dlp breaks when YouTube changes] → Pin a recent version, upgrade it deliberately, and treat a failed source as a per-seed miss.
- [YouTube Music search returns a cover or live version] → Fingerprint verification flags it as `mismatch`, and the seed can be fixed with an explicit video ID.
- [AcoustID's free key is rate-limited to about 3 requests per second] → Sequential lookups stay well under it.
- [Deezer preview URLs expire] → Download right after search, and never store the URL.
- [Legal and terms] → Already accepted in ADR 0007. Audio stays on the owner's disk, and the spec forbids serving it.

## Migration Plan

Migration `0009_audio_assets` is additive. The API applies it on start, and nothing in the API uses the table. To roll back, run `alembic downgrade 0008_per_user_authorization` and delete the audio directory if it's no longer wanted.
