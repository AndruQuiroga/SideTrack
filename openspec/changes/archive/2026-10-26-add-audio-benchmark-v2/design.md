# Design

## Context

See proposal.md (Why). Current state:
- **Lab:** `services/audio-lab` embeds a manifest, then writes `report.html` (blind duels, browse) and `metrics.json` (recall, same-artist rate, separation, overlap).
- **Acquisition:** `python -m sidetrack.audio fetch` takes a seed CSV (`artist,title[,album,youtube_id,deezer_id]`) and exports the manifest. Manifest rows carry `artist` and `title` from the seed, plus `track_id` when the catalog resolved one.
- **Lab dependencies:** the lab's core install has no HTTP client (numpy, pyarrow, soundfile, soxr).
- **The owner's export (observed):**
  - 74,826 listens, 2019–2026, with clients Pano Scrobbler, YT Music and the Last.fm importer
  - 29% of listens carry a duration, 70% a YouTube link, 74% a MusicBrainz mapping
  - 6,136 unmapped listens are titled "Artist - Title" under uploader channels
  - 5,415 sessions, using a 30-minute gap; 741 adjacent pairs recur in 3 or more sessions, 342 in 5 or more

## Goals / Non-Goals

**Goals:**
- One reproducible pipeline: export → seeds and labels → fetch → manifest → embed → report with labelled metrics → duels between the two finalists.
- Objective evidence on taste (co-listening), genre (control set) and mood (sleep), so the owner's duels are not the only signal.

**Non-Goals:**
- A general-purpose ListenBrainz importer for Sidetrack. The listening domain already owns ingestion.
- Clustering or genre classification by the models themselves.

## Decisions

### 1. Close out v1 first, provisionally

Archive `add-audio-lab-benchmark` before applying this change:
- **What's recorded:** the owner's decision for run `20261026-223453-0ec1bac` reads "MuQ leads (0.65 against MuQ-MuLan's 0.61, within the 0.05 margin); final pick deferred to the v2 benchmark".
- **Why first:** archiving creates `openspec/specs/analysis/audio-benchmark`, which this change's delta extends. It also keeps v1's evidence separate.
- **Alternative rejected:** folding v2 into the open v1 change. That would mix a finished, recorded run with new behaviour, and v1's tasks are otherwise done.

### 2. Everything lives in the lab, stdlib only for HTTP

- **New modules:** `seeds.py` (ListenBrainz → seeds, labels, co-listening), `control.py` (Deezer charts → seeds, labels) and `labels.py` (reading label files, matching to assets).
- **HTTP:** `control.py` uses `urllib.request` with a 1 request/second throttle and a User-Agent naming the repo, so the lab's core install gains no dependency. Tests inject a fake fetch function.
- **What is not changed:** acquisition (`sidetrack.analysis.audio`) and its database. Both sets go through the existing `fetch` command. Control seeds carry `deezer_id`, so previews resolve directly, and full tracks come from a YouTube Music search.

### 3. Label files are keyed by normalised artist and title

`labels.csv` (`artist,title,label`) and `colisten.csv` (`artist_a,title_a,artist_b,title_b,sessions`) are matched to manifest rows by `_norm(artist)|_norm(title)` from the manifest's own columns. `Asset.seed` isn't used, because it becomes the catalog `track_id` when one resolved. A seed may carry several labels (one row each).

### 4. Cleaning and resolution in `audio-lab seeds`

- **Order of resolution:**
  1. Take the MusicBrainz-mapped artist and recording name when present.
  2. Otherwise, if the title has the form "A - B", use A as the artist and B as the title. Bracketed suffixes such as "(Official Video)" or "[Monstercat Release]" are stripped by the existing normalisation.
  3. Otherwise use the raw fields.
- **Exclusions, each counted in a report:**
  - duration over 600 s, when known
  - pseudo-artists ("A YouTube Labs experiment")
  - podcast patterns: a default list ("best in jest", "podcast", "episode", "ep. \d+") plus `--exclude-pattern`
- **Durations are often unknown** (only 29% of listens have one), so `embed --max-duration 600` is the second line of defence after fetching.

### 5. Balanced selection

- **Eligible tracks:** loved, or played at least twice after cleaning.
- **Sleep share:** sleep-labelled tracks fill up to 15% of personal seeds, taken before the buckets (most night plays first). Sleep tracks are rarely replayed by choice, so play-ordered buckets alone would never reach them.
- **Co-listened pairs first:** take the strongest pairs (most sessions, ties broken by key), keeping both tracks, until 25% of `--count` is filled (`--colisten-share`) or the artist cap blocks a pair.
- **The rest, round-robin over buckets:** each bucket is a (first-play year, play band) combination, with bands 2–3, 4–9 and 10+. Within a bucket, tracks are ordered by plays (descending), then key. This keeps old favourites and recent finds both represented.
- **Artist cap:** at most 2 tracks per primary artist (the first credited name), the same split as acquisition's credit matching.
- **Default size:** 250 personal seeds plus 150 control seeds (15 genres × 10). About 400 seeds is around 8 GB on E:, and about 30 minutes of embedding for all four models at v1's measured rates.
- **Determinism:** no randomness. Every ordering uses explicit sort keys.

### 6. Sleep labels from night sessions

The owner has no sleep playlist. They pick YT Music's sleep filter and let autoplay run, so the signal is in the sessions, not in a list.
- **Night session:** starts between 22:00 and 04:00 in the PC's local timezone, lasts at least one hour, and has at least 12 listens. Observed in the full export: 84 of 5,415 sessions.
- **Sleep label:** a track gets it when at least 2 of its plays, and at least 75% of them, are in night sessions. Observed: 116 tracks. They include ambient and lo-fi artists such as Øneheart, lmnl, Aurenth and hallow. They also include some autoplay drift into EDM, so purity is noisy and is reported against its base rate, never gated.
- **Effect on co-listening:** night sessions are excluded from the co-listening pairs. Unattended autoplay reflects YT Music's choices, not the owner's.

Alternative rejected: an owner-maintained artist list. The owner doesn't keep one, and the session pattern is observable from the data.

### 7. Metrics

All metrics are computed per model, within that model's space (ADR 0004):
- **Genre precision@10:** each control seed's neighbours are ranked among control tracks only. Otherwise the large, single-genre personal pool would swamp the measure.
- **Co-listening hit rate:** over pair directions, using the normal top 10 (all tracks).
- **Sleep purity:** reported with its base rate, because 0.3 means a lot if only 5% of the pool is sleep tracks.
- **Format:** each figure goes into `metrics.json` under the model, with the count of seeds or pairs it covers, and appears on the Results tab.

### 8. Finalist duels and gate v2

- **Finalist duels:** `--duel-model` filters `build_duels` to the named pair. Each seed then yields at most one duel, which gives about 400 duels.
- **Gate v2**, to be written in `docs/AUDIO-BENCHMARK.md`:
  - at least 30 finalist duels on the v2 run
  - genre precision, co-listening hit rate and sleep purity reported for both finalists
  - preview→full recall@10 of 0.8 or more
  - the owner's decision, recorded with the evidence. A finalist that loses both the duels and the co-listening rate is not picked without a stated reason.

## Risks / Trade-offs

- **[Deezer charts change daily]** → `control-seeds` writes its own seeds and labels files. The run is reproducible from those files, not from the live chart.
- **[Channel titles that aren't "Artist - Title", such as compilations or mixes]** → They are left unresolved, and long mixes are caught by the duration limits. The exclusion report shows the counts so the owner can add patterns.
- **[Co-listening reflects autoplay as well as choice]** → Requiring 3 or more separate sessions filters one-off radio runs. The threshold is an option, and the report shows how many pairs remain.
- **[Control tracks via YouTube search can fetch the wrong version]** → AcoustID verification applies as before, and mismatches are excluded from the manifest exactly as in v1.
- **[Personal data leakage]** → Outputs inside the repo are refused, and tests use synthetic exports.

## Migration Plan

None: no database, image or deploy change. Rollback is reverting the lab commits. The v1 run directory and its results remain valid.

## Open Questions

- **Exact genre list:** Deezer's chart IDs are fetched live, and the default excludes "All" and genres with fewer than 10 tracks. The owner may drop or add genres with `--genre`. This doesn't change the design.
