# Proposal

## Why

The owner's library and the club's listens hold several forms of the same music: Deezer
30-second previews beside full files, radio edits, slowed or sped-up edits, remixes and
covers. Today nothing relates them, so the same song can appear twice in neighbours and
stats, or a preview can stand in for a different recording. The research notes are clear
that these are three different tasks: near-identical audio fingerprints, retrieval of
versions of a musical work, and "sounds similar". None of them proves recording identity
on its own, and the MuQ preview benchmark does not justify automatically merging slowed or
sped-up edits (docs/research/MUSIC-ANALYSIS.md, idea 4). This change proposes candidate
related versions for the owner to confirm or reject, and never merges anything itself.

## What Changes

- **Local Chromaprint fingerprints per asset.** Each audio asset gets a stored raw
  Chromaprint fingerprint computed locally with `fpcalc`, with a state (`available`,
  `failed`, `unavailable` when `fpcalc` is missing). No AcoustID lookup is needed for this.
- **`near_identical` candidates** from local fingerprint comparison, with evidence: score,
  offset in each asset, matched duration and whether either side is a preview.
- **`possible_version` candidates** from a learned version-retrieval method (MOVE,
  CoverHunter, or MuQ per ADR 0010), only after an audio-lab run, license and dependency
  review, the owner's decision and an ADR. Until then the kind reports `unavailable`.
- **Operator review.** The operator lists candidates and confirms them with a relation
  (`same_recording`, `preview_of`, `edit_of`, `remix_of`, `cover_of`) or rejects them.
  Rejected pairs are not re-proposed by the same method version. Decisions are reversible.
- **An audio-lab version benchmark** that scores methods on altered audio (time-stretch with
  and without pitch preservation, resampled speed changes, trims, re-encodes) and on hard
  negatives (same artist with a different song, close MuQ-MuLan neighbours).

### Out of scope

- Merging tracks, assets or listens, or creating listen-to-audio links from confirmations.
  A confirmed relation is recorded only; using it (for example a `recognition` link method
  or deduplicated stats) is a follow-up change.
- Any HTTP route or web UI for candidates or relations.
- Using MuQ-MuLan pooled similarity, mood, themes or any "sounds similar" score as
  candidate evidence.
- AcoustID or MusicBrainz lookups beyond what asset verification already does.
- Public cover-song datasets that require YouTube downloads; yt-dlp stays opt-in and
  personal-only.

## Capabilities

### New Capabilities

- `analysis/version-candidates`: per-asset fingerprints, candidate related-version pairs
  with evidence and method version, operator confirmation and rejection, and the gate for
  learned version methods.

### Modified Capabilities

- `analysis/audio-benchmark`: version-retrieval runs on altered audio and hard negatives,
  with license and dependency records.

## Impact

- **Observed:** `sidetrack/analysis/audio/verify.py` already fingerprints fetched audio with
  Chromaprint (`fpcalc` through pyacoustid, `audio` extra) and looks the fingerprint up in
  AcoustID; only the match score is kept (`acoustid_score` in
  `sidetrack/analysis/models.py`). The fingerprint itself is not stored.
- **Observed:** audio assets carry a preview/full distinction and one pooled MuQ-MuLan
  vector each (`sidetrack/analysis/models.py`, `sidetrack/analysis/embeddings/registry.py`);
  production holds 862 assets.
- **Observed:** nothing in the schema relates two assets or two tracks as versions.
- **Observed:** ADR 0010 (docs/decisions) says MuQ is added when a feature needs recognition
  or artist grouping; the `resolve-listens-to-audio` draft leaves room for a `recognition`
  link method and a follow-up `add-muq-recognition`.
- **Assumed:** raw fingerprints are a few KiB per asset (about 8 values per second as 32-bit
  integers), so 862 assets need a few MiB; the size is measured in task 4.2.
- **Assumed:** Chromaprint matching degrades under speed and pitch changes; task 3.3
  measures how far.
- **Assumed:** MOVE and CoverHunter code, weights and training-data terms have not been
  reviewed; their licenses are not asserted here.

### Affected

- `sidetrack/analysis/` (fingerprint store, candidate generation, review CLI), a migration,
  `services/audio-lab` (version benchmark), docs/AUDIO.md, docs/AUDIO-BENCHMARK.md.

## Dependencies

- None required to compute fingerprints or candidates; they work on assets alone.
- Related: `resolve-listens-to-audio` (sonic similarity never creates a link; confirmed
  relations do not change its links in this change) and the follow-up `add-muq-recognition`.
- Related: `add-timestamped-audio-windows` (window vectors could later localize a preview
  inside a full track; not required here).
