# analysis/listen-audio-resolution Specification

## Purpose
Defines how catalog tracks are linked to the audio assets that represent them, which asset
stands for a track when several do, and how the audio coverage of a user's plays is
reported, so every audio-derived statistic can say what share of listening it rests on.

## Requirements

### Requirement: Links are stored with their method and version

Each link SHALL join one catalog track to one audio asset and record the method that made it (`recording_mbid`, `youtube_id`, `seed_identity`, `seed` or `manual`), a confidence between 0 and 1, the matcher version and when it was made. A track MAY link to several assets and an asset to several tracks. The same track and asset SHALL have at most one link.

#### Scenario: Full track and preview both linked

- **WHEN** a track matches an asset's full track and its preview
- **THEN** two links exist for the track, one per asset, each with its method and confidence

#### Scenario: Duplicate link rejected

- **WHEN** a second link for the same track and asset is written
- **THEN** the database rejects it and one link remains

### Requirement: Links keep the evidence that made them

Each link SHALL store the evidence values it matched on: the shared recording MBID, the YouTube video ID, or the normalised artist and title keys. A read of a link SHALL return its method, confidence and evidence, so a person can see why a track and asset were joined.

#### Scenario: Evidence on a seed identity link

- **WHEN** a `seed_identity` link is read
- **THEN** it returns the normalised artist and title key that both sides shared

### Requirement: Ambiguous seed identity is exposed, not resolved silently

When one normalised artist and title key matches more than one track or more than one asset of the same kind, the matcher SHALL still write the links but mark them `ambiguous`. The audio-for-track operation SHALL report `ambiguous` with the candidates instead of choosing among ambiguous links by itself.

#### Scenario: Two tracks share a key

- **WHEN** tracks "Song" (album) and "Song" (live) normalise to the same key as one asset
- **THEN** both links are marked `ambiguous` and the audio-for-track read for either track reports `ambiguous` with the asset listed

### Requirement: Operators can correct links

An operator SHALL be able to reject a link, which SHALL remove it from reads and stop the matcher from recreating it for that track and asset, and to confirm an ambiguous link, which clears `ambiguous` for that pair. Corrections SHALL be recorded with time and SHALL survive matcher reruns.

#### Scenario: Reject a wrong link

- **WHEN** the operator rejects a `seed_identity` link and the matcher runs again
- **THEN** the link is not recreated and the rejection is listed in the report

### Requirement: Sonic similarity never creates a link

The matcher SHALL NOT link a track and an asset because their embeddings are similar. Nearest-neighbour results SHALL NOT be presented as the same recording.

#### Scenario: Close neighbour, different metadata

- **WHEN** an unlinked asset's nearest neighbour belongs to a linked track with a different artist and title
- **THEN** no link is created

### Requirement: Recording MBIDs link with full confidence

When a track's MusicBrainz recording ID equals an asset's AcoustID-confirmed recording MBID, the matcher SHALL link them with method `recording_mbid` and confidence 1.0.

#### Scenario: Confirmed recording

- **WHEN** a track has recording MBID M and an asset confirmed by AcoustID has recording MBID M
- **THEN** a link with method `recording_mbid` and confidence 1.0 exists

### Requirement: YouTube IDs on a track's listens link its uploads

When any listen of a track records a YouTube video ID equal to an asset's YouTube source reference, the matcher SHALL link them with method `youtube_id` and confidence 1.0.

#### Scenario: Upload played from the same video

- **WHEN** a track's listens include origin video `abc123` and a YouTube Music asset has source reference `abc123`
- **THEN** a link with method `youtube_id` exists between them

### Requirement: Seed identity links by normalised artist and title

When an asset's seed artist and title, normalised the same way as imported listens, equal a track's normalised artist and title, the matcher SHALL link them with method `seed_identity` and confidence 0.9. A match on title alone, or on artist alone, SHALL NOT create a link.

#### Scenario: Same artist and title

- **WHEN** an asset was fetched for seed "Some Artist" / "Deep Cut" and a track is "some artist" / "Deep Cut (Official Video)" before normalisation
- **THEN** a `seed_identity` link exists

#### Scenario: Title only

- **WHEN** an asset's seed title equals a track's title but the artists differ
- **THEN** no link is created and the track is counted as unlinked

### Requirement: Existing seed links are preserved

An asset whose `track_id` was set at acquisition SHALL get a link to that track with method `seed` and confidence 1.0 when the matcher runs.

#### Scenario: Acquisition-time link

- **WHEN** an asset has `track_id` T and the matcher runs
- **THEN** a link between T and the asset exists with method `seed`

### Requirement: The matcher is idempotent and versioned

Running the matcher again SHALL add no duplicate links, SHALL keep `manual` links, and SHALL replace links made by an older matcher version with the current version's result for the same track and asset.

#### Scenario: Run twice

- **WHEN** the matcher runs twice on unchanged data
- **THEN** the link count is unchanged after the second run

#### Scenario: Manual link kept

- **WHEN** an operator has linked a track and asset manually and the matcher runs
- **THEN** the manual link remains with method `manual`

### Requirement: One asset represents a track

The audio-for-track operation SHALL return the track's preferred asset: an asset with a current embedding before one without, then a full track before a preview, then an AcoustID-confirmed asset before an unverified one. It SHALL report `no_audio` for a track with no linked asset, `ambiguous` when only ambiguous links exist, and `no_embedding` when no linked asset has a current embedding.

#### Scenario: Full preferred over preview

- **WHEN** a track links to an embedded preview and an embedded full track
- **THEN** the operation returns the full track

#### Scenario: Track without audio

- **WHEN** a track has no links
- **THEN** the operation reports `no_audio` and returns no asset

### Requirement: Coverage is reported per user and period

For a user and a time range the coverage operation SHALL report the number of plays and of included plays (those whose session's effective classification is not autoplay), how many of each resolve to an asset with a current embedding, and counts of the rest by reason: `no_link`, `ambiguous`, `no_embedding`, `file_missing`. Shares SHALL be computed from these exact counts.

#### Scenario: Partial coverage

- **WHEN** a user has 100 plays in a week, 80 of them included, 56 included plays resolve to embedded assets, 20 included plays have no link and 4 have an asset with no embedding
- **THEN** the report gives included coverage 56 of 80 with `no_link: 20` and `no_embedding: 4`

#### Scenario: Nothing linked

- **WHEN** a user's plays in the period link to no asset
- **THEN** the report gives coverage 0 with every play counted under `no_link`, and no share is invented

### Requirement: Linking is operator-started and reported

The matcher SHALL run only from the operator command or a job the operator queues. Its result SHALL report links made per method, tracks left unlinked, and assets left unlinked, as exact counts.

#### Scenario: Operator run

- **WHEN** the operator runs the link command over a catalog where 700 of 862 assets match by seed identity, 120 by YouTube ID and 42 match nothing
- **THEN** the output lists `seed_identity: 700`, `youtube_id: 120`, unlinked assets 42, and the unlinked tracks count
