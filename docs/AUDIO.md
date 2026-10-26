# Audio acquisition

`python -m sidetrack.audio` fetches audio for analysis on the owner's machine. It's
personal and opt-in (ADR 0007): never scheduled, never run by a service, and never
served over HTTP. The audio lab benchmark (`add-audio-lab-benchmark`) reads the
manifest this command exports.

YouTube's terms prohibit downloading, and private copies of streamed tracks aren't
clearly lawful. The owner accepted that for personal use in ADR 0007. Deezer previews
are subject to Deezer's API terms. Nothing fetched is redistributed.

## Setup (once)

1. Install the Python extra: `uv sync --python 3.11 --extra api --extra worker --extra dev --extra audio`
2. Install **Chromaprint's `fpcalc`**, **ffmpeg** and **deno**, and put them on `PATH`.
   YouTube now requires a JavaScript challenge solver: yt-dlp runs the official
   `yt-dlp-ejs` scripts (pinned in the `audio` extra) with deno. Without deno, some
   downloads fail with "n challenge solving failed".
   - Windows: `scoop install chromaprint ffmpeg deno`
   - Debian/Ubuntu: `sudo apt install libchromaprint-tools ffmpeg`, plus deno from <https://deno.com>
   - Check: `fpcalc -version`, `ffmpeg -version` and `deno --version`
3. Register an application at <https://acoustid.org/new-application> (free) and use its
   **application API key**. The user API key on your account page is for submitting
   fingerprints, and lookups reject it as "invalid API key".
4. Set these, in `.env` or the shell (see `config/ENVIRONMENT.md`):
   ```
   DATABASE_URL=postgresql+psycopg://…        # the database to record assets in
   SIDETRACK_AUDIO_DIR=D:/sidetrack/audio     # on the HDD
   SIDETRACK_AUDIO_FETCH_ENABLED=true
   ACOUSTID_API_KEY=…
   SIDETRACK_AUDIO_RETENTION_DAYS=365         # optional; needed only for prune
   ```
5. Apply migrations: `uv run --frozen --extra api alembic upgrade head` (adds `audio_assets`).

## Seed list

A CSV with a header row. `artist` and `title` are required; the other columns are optional.

```csv
artist,title,album,youtube_id,deezer_id
Broadcast,Come On Let's Go,The Noise Made by People,,
Stereolab,French Disko,,,
Some Obscure Band,Deep Cut,,dQw4w9WgXcQ,
```

- **`album`** lets catalog resolution create a missing catalog track. Without it, assets
  link only to tracks already in the catalog. Unresolved seeds are still fetched and keep
  the artist and title you gave.
- **`youtube_id` / `deezer_id`** skip the search. Use them to fix a seed whose search
  picked the wrong upload (reported as `MISMATCH`).

For the benchmark, aim for about 100 seeds, including obscure tracks you know well
enough to judge their neighbours.

## Commands

```bash
uv run --frozen --extra api --extra audio python -m sidetrack.audio fetch --seeds seeds.csv
uv run --frozen --extra api --extra audio python -m sidetrack.audio fetch --seeds seeds.csv --only preview
uv run --frozen --extra api --extra audio python -m sidetrack.audio fetch --seeds seeds.csv --cookies C:/private/yt-cookies.txt
uv run --frozen --extra api --extra audio python -m sidetrack.audio manifest --out manifest.csv
uv run --frozen --extra api --extra audio python -m sidetrack.audio verify
uv run --frozen --extra api --extra audio python -m sidetrack.audio prune
```

- **`fetch`** gets the full track (YouTube Music, native best audio, not transcoded) and
  the 30-second Deezer preview for each seed. It stores each file once as
  `<SIDETRACK_AUDIO_DIR>/<sha256>.<ext>`, fingerprints it, and records it. Reruns are
  safe, because already-stored audio is reused. Requests are paced at about one per second per
  source.
- **`--cookies`** passes a Netscape-format cookie file to yt-dlp. It's only needed if
  YouTube asks for sign-in. Its path and contents never appear in logs, rows or output.
  Keep it outside the repo.
- **`manifest`** writes one row per asset whose file still exists: path (relative to the
  audio directory), sha256, kind, source, source_id, duration_s, verification, track_id,
  artist, title.
- **`verify`** re-checks every `unverified` asset whose file exists, for example after
  adding `ACOUSTID_API_KEY`, without fetching again.
- **`prune`** deletes files older than `SIDETRACK_AUDIO_RETENTION_DAYS` and keeps their rows.

## Reading the summary

```
Seeds: 100  new assets: 187  already stored: 0
Verification: 141 confirmed, 6 mismatch, 40 unverified
  unverified because no match: 38
  unverified because AcoustID lookup failed: 2
  MISMATCH youtube_music: Some Band - Some Song
  missing deezer_preview: Obscure Band - Deep Cut (no result)
```

- **confirmed:** AcoustID's confident match (score ≥ 0.8) has the seed's artist and title.
- **mismatch:** a confident match names a different recording, such as a cover, live
  version or wrong upload. The file and row are kept. Fix the seed with an explicit ID and refetch.
- **unverified:** no confident match, or verification couldn't run (no `fpcalc`, no key,
  or the service was down). Previews often land here, since 30 seconds fingerprints poorly.
  Their Deezer ID was chosen by metadata.

## Smoke run (2026-10-26, owner's PC)

Run against a local Postgres 16 (migrated to `0009_audio_assets`) with
`SIDETRACK_AUDIO_DIR=E:/sidetrack/audio` on the HDD, using five seeds: Broadcast
"Come On Let's Go", Radiohead "Reckoner", Portishead "Roads", Aphex Twin "Avril 14th"
(each with album) and Stereolab "French Disko" (no album).

| Run | New assets | Already stored | Missing | Notes |
| --- | --- | --- | --- | --- |
| 1 | 5 (all full) | 0 | 5 previews | Deezer's `artist:"…" track:"…"` search now returns nothing; fixed to plain-text search filtered by artist and title |
| 2 | 5 (all previews) | 4 | 1 full | Reruns reused identical audio. Radiohead failed once deno was present without the solver scripts; fixed by pinning `yt-dlp-ejs` |
| 3 | 0 | 10 | 0 | Clean, with no yt-dlp warnings |

- All 10 files exist under the audio directory. `fpcalc` durations match the tracks
  (full tracks 125 to 303 s, previews 29 s).
- The 4 seeds with an album are linked to catalog tracks. Stereolab, which had no album, is unlinked as designed.
- `manifest` wrote 10 rows.
- **Verification: 0 confirmed, 0 mismatch, 10 unverified**, because no AcoustID key was
  configured yet. Fingerprinting ran, but the lookup didn't. To finish task 4.2, the
  owner adds `ACOUSTID_API_KEY` and runs `verify`. "Audio acquisition" stays
  **partial** until that confirms real matches.
