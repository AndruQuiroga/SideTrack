# Proposal

## Why

Sidetrack now has two halves of the picture that never touch: 862 embedded audio assets
(analysis) and the listens that will arrive from ListenBrainz (listening, via catalog tracks).
Not one production asset is linked to a catalog track, because `import-manifest` drops
track links by design. Until a play can be traced to the audio it was a play of, no
profile, visual or compatibility score can weight sound by listening, and no honest
coverage figure ("71% of this week's included plays have audio") can be shown.

## What Changes

- **Track–audio links.** A new analysis-owned mapping from catalog tracks to audio assets,
  many-to-many, with the method that made each link (`recording_mbid`, `youtube_id`,
  `seed_identity`, `seed`, `manual`), a confidence, and a matcher version. A track can link
  to its full track and its preview; one asset can serve several tracks until they are merged.
- **A matcher** that links tracks to assets using only evidence already stored: the
  recording MBID on both sides; the YouTube video IDs recorded on a track's listens against
  the asset's YouTube source reference; and the asset's seed artist and title against the
  track's normalised artist and title. It never fetches, never embeds, never guesses on
  partial matches, and reports every count. Each link keeps the evidence it matched on.
  When one key fits several tracks or assets, the links are marked `ambiguous` and not
  resolved silently. Operators can reject or confirm links, and corrections survive reruns.
  Sonic similarity never creates a link (research notes §6.2).
- **Audio-for-track read model.** A public analysis operation returns the preferred asset for
  a track (embedded over not, then full over preview, then confirmed over unverified) and says plainly
  when a track has none.
- **Coverage report.** For a user and period, the share of plays, and of included plays
  (effective session classification not autoplay), that resolve to an asset with a current
  embedding, broken down by why the rest don't (`no_link`, `ambiguous`, `no_embedding`,
  `file_missing`). Downstream features must show this number.
- **Operator command** `python -m sidetrack.audio link` runs the matcher and prints the
  report; an optional job lets it run on the rack after imports.

Out of scope:

- Merging edits and versions of one recording (slowed, sped-up, remixes) by audio
  recognition. MuQ-MuLan's preview→full recall@1 is 0.66; MuQ's 0.96 makes it the model for
  that, and ADR 0010 reserves adding MuQ for the first recognition feature. That is a
  follow-up change (`add-muq-recognition`); the link table leaves room for a `recognition`
  method.
- Fetching audio for tracks that have none. Acquisition stays opt-in (ADR 0007); the coverage
  report is the input to the owner's next seed list, not a trigger.
- Any web page or bot command; the weekly profile and visuals consume the read models.

## Capabilities

### New Capabilities

- `analysis/listen-audio-resolution`: how catalog tracks are linked to audio assets, which
  asset represents a track, and how audio coverage of a user's plays is reported.

### Modified Capabilities

None. `analysis/audio-assets` and `analysis/audio-embeddings` are unchanged; this change
reads them.

## Impact

Current state:

- **Observed:** `audio_assets.track_id` is nullable and `import-manifest` "drops catalog
  track links, which belong to the other database" (docs/AUDIO.md); the production assets
  were imported that way (docs/STATUS.md, "862 assets were imported to production on
  2026-10-31"), so the column is null for all of them. Assets keep `seed_artist`,
  `seed_title`, `source`/`source_ref` (the YouTube video ID or Deezer track ID) and
  `recording_mbid` when AcoustID confirmed them (`sidetrack/analysis/models.py`).
- **Observed:** `similar_assets` excludes neighbours by the asset's own track or seed
  (`openspec/specs/analysis/audio-embeddings`), so a track-level identity already matters
  to the one embedding consumer that exists.
- **Observed:** listen metadata will carry each listen's YouTube ID and recording MBID after
  `import-listenbrainz-history` (its design, Decision 5); Last.fm listens carry only the
  Last.fm payload.
- **Assumed:** most of the owner's 862 assets will match an imported track by seed identity,
  because the seeds were built from the same export with the same normalisation
  (`audio_lab/seeds.py`); task 4.1 measures the real match rate.

Affected:

- `sidetrack/analysis/` (new `links` module, read models, `link` subcommand in
  `sidetrack/audio.py`), `sidetrack/job_runner.py` for the optional job, `migrations/` (0014).
- Docs: `docs/AUDIO.md` (link command, coverage), `docs/MODULES.md` (new table),
  `docs/status.yaml`.
- Depends on `import-listenbrainz-history` for imported tracks and listen metadata; it can
  be implemented against Last.fm-only data but will link little without it.
