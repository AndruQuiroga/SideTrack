# Spec Delta

## Purpose

Reports, for one user, period and analysis facet, which plays an audio-derived result
rests on and why the rest are excluded, with each track's analysis state, analyzed
duration and the review queues that let the user correct sessions and links.

## ADDED Requirements

### Requirement: Coverage partitions a period's plays
For a user, period and facet, the coverage read model SHALL report total plays, excluded plays (sessions whose `effective_kind` is `night_autoplay`), and included plays split into `full_usable`, `preview_usable`, `linked_not_usable` and `no_confident_link`. The buckets SHALL sum to included plays, and included plus excluded SHALL equal total plays. `no_confident_link` SHALL be broken down by the resolution reasons `no_link` and `ambiguous`.

#### Scenario: Mockup week
- **WHEN** a week has 90 plays, 6 in sessions whose `effective_kind` is `night_autoplay`, and of the 84 included plays 45 resolve to full assets with a current embedding, 16 to previews with a current embedding, 9 to linked assets without one, 10 have no link and 4 have only ambiguous links
- **THEN** the report gives total 90, excluded 6, included 84, buckets 45, 16, 9 and 14, and `no_confident_link` broken down as `no_link: 10` and `ambiguous: 4`

#### Scenario: Imported period with no plays
- **WHEN** the user's import coverage includes the period and it holds no plays
- **THEN** the report gives total 0 with every bucket 0 and the state `no_listens`, and no share is computed

### Requirement: Periods outside import coverage are not zero
When any part of the requested period lies outside the user's per-account import coverage, the report SHALL state `not_imported` for those spans with their dates, and SHALL NOT report them as periods with zero listens.

#### Scenario: Period before the import
- **WHEN** coverage is requested for a week before the earliest imported listen of every linked account
- **THEN** the report states `not_imported` for that week and gives no bucket counts and no `no_listens` state

#### Scenario: Partly imported period
- **WHEN** a requested month has its first 10 days outside import coverage
- **THEN** the report lists those 10 days as `not_imported` and counts plays only for the imported days

### Requirement: Coverage is computed per facet
Coverage SHALL be computed for one named facet, and a play counts as usable only if that facet has a current result for its track's representative asset. An unknown facet SHALL be rejected; a known facet whose analysis is not implemented SHALL report `facet_unavailable` and no buckets.

#### Scenario: Different denominators
- **WHEN** 61 included plays have a current embedding and 40 of them have a current mood score
- **THEN** `embedding` coverage reports 61 usable plays and `mood` coverage reports 40

#### Scenario: Facet not implemented
- **WHEN** coverage is requested for `mood` before mood scores exist
- **THEN** the response reports `facet_unavailable` for `mood` and contains no bucket counts

#### Scenario: Unknown facet
- **WHEN** coverage is requested for facet `danceability`
- **THEN** the API responds 422 naming the facet

### Requirement: Each track has one explicit analysis state per facet
For a facet, each included track SHALL have exactly one state: `available`, `no_audio`, `ambiguous`, `file_missing`, `not_computed`, `stale_model` or `failed`. `no_audio` and `ambiguous` SHALL follow the track's `audio_for_track` status; `stale_model` SHALL mean a result exists only for another model, checkpoint or pipeline; `failed` SHALL carry the stored reason. No state SHALL default to `available`.

#### Scenario: Older pipeline
- **WHEN** a track's only embedding has pipeline `w10-t3-cap180-fp32-mean-l2-v0` and the current pipeline is `-v1`
- **THEN** its `embedding` state is `stale_model` and its play is counted under `linked_not_usable`

#### Scenario: Decode failure
- **WHEN** the latest embedding attempt for a track's asset failed with `decode_failed`
- **THEN** its state is `failed` with reason `decode_failed`

#### Scenario: Ambiguous link
- **WHEN** `audio_for_track` reports `ambiguous` for a track
- **THEN** its state is `ambiguous` and its plays are counted under `no_confident_link` with reason `ambiguous`

#### Scenario: Linked file missing
- **WHEN** a track's representative asset has a link but its file has been deleted
- **THEN** its state is `file_missing` and its plays are counted under `linked_not_usable`

### Requirement: Analysis outcomes are stored
Every analysis attempt for an asset and facet SHALL store its outcome (`succeeded` or `failed` with reason), model, checkpoint revision, pipeline and time, independently of job cleanup. A later success SHALL supersede an earlier failure for the same revisions.

#### Scenario: Failure survives job cleanup
- **WHEN** an embedding job reports `decode_failed` for an asset and the finished job row is deleted
- **THEN** the asset's `embedding` outcome is still `failed` with reason `decode_failed`

#### Scenario: Retry succeeds
- **WHEN** a failed asset is embedded successfully at the same revisions
- **THEN** its `embedding` state becomes `available`

### Requirement: Usable plays report source and analyzed duration
For each usable track, coverage detail SHALL report whether the representative asset is full or preview, its duration, and the seconds analyzed under the facet's pipeline. When the asset duration is unknown, analyzed duration SHALL be reported `unknown` rather than estimated.

#### Scenario: Long full track
- **WHEN** a usable track's full asset lasts 312 s under a pipeline that analyzes at most the first 180 s
- **THEN** detail reports `full`, duration 312 s and analyzed 180 s

#### Scenario: Unknown duration
- **WHEN** the asset has no stored duration
- **THEN** detail reports analyzed duration `unknown`

### Requirement: Period aggregates report insufficient samples
When a facet's usable plays in a period fall below the minimum the consuming feature declares, the coverage report SHALL include `insufficient_sample` with the usable count and the minimum, and SHALL still report all buckets.

#### Scenario: Thin week
- **WHEN** a week has 12 usable `mood` plays and the weekly profile's minimum is 20
- **THEN** the report includes `insufficient_sample` with 12 of 20 and the four bucket counts

### Requirement: Exclusions are disclosed and follow user overrides
The report SHALL list sessions in the period that are flagged `night_autoplay`, `unclassified` or `unknown`, or carry a user override, with start, end, listen count, rule version, rule kind, override (`keep` or `autoplay`) and `effective_kind`. Inclusion SHALL follow `effective_kind` only, and the next report after an override SHALL reflect it.

#### Scenario: Keep override re-includes plays
- **WHEN** a 14-play session flagged `night_autoplay` receives the user's `keep` override
- **THEN** the next report's excluded count falls by 14, included plays rise by 14, and the session is listed with override `keep`

#### Scenario: Autoplay override excludes plays
- **WHEN** an `unclassified` session of 8 plays receives the user's `autoplay` override
- **THEN** the next report's excluded count rises by 8 and the session's `effective_kind` is listed as `night_autoplay`

#### Scenario: Unknown session
- **WHEN** a session is `unknown` because the user has no timezone
- **THEN** it is listed as `unknown` with its plays counted as included, and the report states `timezone_missing`

### Requirement: Links needing review are listed with evidence
The review queue SHALL list tracks with included plays in the period whose `audio_for_track` status is `no_audio` or `ambiguous`, ordered by play count, each with candidate links, method, confidence, `ambiguous` flag and stored evidence. Confirming or rejecting a link SHALL go through the resolution operation; audio similarity SHALL NOT propose or create a link.

#### Scenario: Confirm an ambiguous link
- **WHEN** the owner confirms link A for an ambiguous track with 9 included plays whose asset has a current embedding
- **THEN** the next report moves those 9 plays from `no_confident_link` to a usable bucket

#### Scenario: Reject a link
- **WHEN** the owner rejects the only link of a track
- **THEN** the next report counts its plays under `no_link`

#### Scenario: No similarity candidates
- **WHEN** a track has no link and an asset with high cosine similarity to its other plays exists
- **THEN** the queue offers no candidate derived from similarity

### Requirement: Coverage and review are owner-only
Coverage, track detail and review queues SHALL be returned only to the user they describe, whatever their `listening_visibility`. Other callers SHALL receive 404. Session overrides SHALL act only on the acting user's sessions; link confirmation and rejection SHALL follow the resolution capability's operator permission.

#### Scenario: Club member requests coverage
- **WHEN** member U requests V's coverage and V's visibility is `club`
- **THEN** the API responds 404

### Requirement: Coverage never acquires or serves audio
Coverage and review responses SHALL contain no audio data, audio file paths or stream URLs, and no coverage or review action SHALL queue audio acquisition.

#### Scenario: Missing audio listed only
- **WHEN** the report lists 14 included plays with no confident link
- **THEN** the response contains track metadata and counts only, and no acquisition job is enqueued
