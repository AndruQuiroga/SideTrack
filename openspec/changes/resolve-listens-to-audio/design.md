# Design

## Context

See proposal.md (Why, Impact). Constraints that shape the approach:

- **Evidence on both sides is already stored.** Assets: `seed_artist`, `seed_title`, `source`
  (`youtube_music` | `deezer_preview`), `source_ref` (video or Deezer ID), `recording_mbid`,
  `verification`, `kind`, `file_deleted_at`. Tracks: `artist_name`, `title`, `musicbrainz_id`.
  Listens (after `import-listenbrainz-history`): `metadata.listenbrainz.youtube_id` and
  `recording_mbid`.
- **Normalisation must match the import.** `import-listenbrainz-history` ports
  `audio_lab/seeds.py`'s `_norm` and `clean_title`; the matcher must call the same
  functions, or seed identity silently stops matching.
- **Scale.** Hundreds to low thousands of assets against 10,000–15,000 tracks: three
  SQL joins, not a nearest-neighbour problem.
- **Boundaries.** Analysis owns `audio_assets` and may read catalog and listening read
  models; it must not write `tracks` or `listen_events` (docs/MODULES.md).

## Goals / Non-Goals

**Goals:**
- Make every production asset reachable from a track, and every linked play reachable from
  an embedding, with the method recorded.
- Give downstream changes one read model for "the audio of this track" and one for coverage.

**Non-Goals:**
- Guessing. Partial or fuzzy matches (edit distance, title-only) are not links.
- Identity across versions of a recording (recognition). Reserved for `add-muq-recognition`.

## Decisions

### Decision 1: A link table rather than `audio_assets.track_id`

`track_audio_links(id, track_id → tracks CASCADE, asset_id → audio_assets CASCADE, method,
confidence, matcher_version, linked_at)`, unique `(track_id, asset_id)`, analysis-owned.
`audio_assets.track_id` keeps its meaning ("fetched for this track") and is copied into the
table as a `seed` link.

Why: one asset legitimately serves several tracks until uploads are merged (two tracks
"Artist - Song" and "Song" that the import didn't fold together), and one track has a full
track and a preview. A single nullable column can't express either.

Alternative: set `audio_assets.track_id` and add `preview_of_asset_id`. Rejected: it
couples acquisition records to a changing resolution, and can't hold a method per link.

### Decision 2: Three deterministic matchers, run in confidence order

1. `recording_mbid`: `tracks.musicbrainz_id = audio_assets.recording_mbid` where
   `verification = 'confirmed'`. Confidence 1.0.
2. `youtube_id`: distinct `(track_id, youtube_id)` pairs from listen metadata joined to
   `audio_assets.source = 'youtube_music' AND source_ref = youtube_id`. Confidence 1.0.
   Reading listen metadata is a listening read model (`listening.track_video_ids(user?)`),
   exported for analysis; analysis does not query `listen_events` directly.
3. `seed_identity`: `norm(seed_artist) || '|' || norm(seed_title) = norm(artist_name) || '|'
   || norm(clean_title(title))`. Confidence 0.9. Computed in Python over the asset list and
   a dictionary of track keys (15,000 strings), because the normaliser is Python; a stored
   `match_key` column is not added to catalog in this change.

Each matcher inserts `ON CONFLICT (track_id, asset_id) DO UPDATE` only when the stored
`matcher_version` is older and the method isn't `manual`. `matcher_version = "links-v1"`.

Alternative: fuzzy title matching. Rejected: "Song (slowed)" and "Song" are different
recordings for the profile's purposes until recognition says otherwise.

### Decision 3: Preferred asset is a sort, not a flag

`audio_for_track(db, track_id)` orders linked assets by `(kind = 'full', verification =
'confirmed', has current embedding, confidence DESC, fetched_at DESC)` and returns the first,
with `status` in `ok | no_audio | no_embedding`. No "primary" flag is stored, so a new
embedding or a pruned file changes the answer without a write.

### Decision 4: Coverage joins plays to sessions and links

`audio_coverage(db, user_id, start, end)` counts plays in the range, chosen plays (session
kind `active` or `unknown`; `night_autoplay` excluded), and for chosen and all plays the
number whose track has a preferred asset with status `ok`; the rest are bucketed by the
preferred asset's status (`no_link` when no links, `no_embedding`, `file_missing` when the
only linked assets are pruned). It returns counts; callers derive shares. This is the
number the weekly profile and every chart must print.

### Decision 5: Operator command, optional job

`python -m sidetrack.audio link [--user <id>] [--queue]` runs the matchers in-process and
prints the report, or queues `analysis.link_audio` on the `default` queue (`--queue`) so the
rack can run it after a ListenBrainz sync. `python -m sidetrack.audio coverage --user <id>
--weeks 4` prints coverage. `link --manual <track-id> <asset-id>` writes a `manual` link.
Nothing schedules linking in this change; the ListenBrainz sync schedule can chain it later.

## Risks / Trade-offs

- [Seed identity matches a wrong track with the same artist and title (a different
  version)] → Confidence 0.9 marks it; recognition later can demote it. The owner's seed
  list used the same keys, so these are the tracks the seeds were built from.
- [Normaliser drift between import and matcher] → Both import the same functions; a test
  links a fixture through both paths.
- [Coverage is low at first] → That is the honest number. The report's `no_link` list is
  the owner's next seed list.
- [Listening read model for video IDs exposes a new cross-domain surface] → It returns only
  `(track_id, video_id)` pairs; no listen rows cross the boundary.

## Migration Plan

1. Apply migration 0014 (`track_audio_links`). Additive.
2. Run `python -m sidetrack.audio link` after the ListenBrainz import; record counts in
   docs/AUDIO.md.
3. **Rollback:** downgrade drops the table; nothing else changes.
