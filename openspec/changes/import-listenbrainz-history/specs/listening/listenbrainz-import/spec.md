# Spec Delta

## Purpose

Defines how a user's ListenBrainz listening history enters Sidetrack: full backfill and
incremental sync through the public API or from an export, how each listen is normalised
and resolved to a catalog track without dropping plays, and what every import reports.

## ADDED Requirements

### Requirement: ListenBrainz listens are imported for a linked public account
The system SHALL import listens for a user from the ListenBrainz account linked to that user, using the public listens API without a credential. A backfill SHALL page backwards from the newest listen until the account's history is exhausted or a given earliest time is reached. Each imported listen SHALL be stored with source `listenbrainz` and the time ListenBrainz recorded.

#### Scenario: Full backfill
- **WHEN** the operator starts a backfill for a user whose linked ListenBrainz account has 2,500 listens and the API returns at most 1,000 per page
- **THEN** the import finishes with 2,500 listen events stored with source `listenbrainz`, having made at most 4 listens requests

#### Scenario: Account not linked
- **WHEN** an import is started for a user with no linked ListenBrainz account
- **THEN** the import fails with the safe outcome `account_not_linked` and stores nothing

### Requirement: Incremental sync resumes from the checkpoint
After a backfill, an import without an explicit start time SHALL fetch only listens newer than the account's checkpoint, and SHALL advance the checkpoint only with committed listens, as `listening/import-checkpoints` requires.

#### Scenario: Sync after new plays
- **WHEN** 30 listens were recorded on ListenBrainz after the last import and a sync runs
- **THEN** exactly those 30 listens are stored, the checkpoint equals the newest listen's time, and no earlier listen is requested again

### Requirement: Export files import through the same normaliser
The operator command SHALL accept a ListenBrainz export directory and import its `listens/*.jsonl` records with the same normalisation, resolution and duplicate handling as the API path. The export path and its contents SHALL NOT appear in stored rows, logs or job results beyond counts.

#### Scenario: Export and API agree
- **WHEN** the same listen is imported once from an export file and once from the API
- **THEN** one listen event exists, and its track, played time and recorded identifiers are identical whichever path ran first

### Requirement: Listens are normalised before resolution
For each listen the system SHALL take the artist and title from ListenBrainz's MusicBrainz mapping when present; otherwise split a title of the form "Artist - Title" when the submitted artist is an upload channel; otherwise use the submitted artist and title. Bracketed upload noise such as "(Official Video)" SHALL be removed from titles. The release name, recording MBID, duration and origin URL SHALL be kept on the listen.

#### Scenario: Mapped listen
- **WHEN** a listen carries a `mbid_mapping` with a recording MBID and artist credits
- **THEN** the stored listen's track has that recording MBID, the mapped artist credit and the mapped recording name

#### Scenario: Channel upload
- **WHEN** a listen's artist is an upload channel and its title is "Some Artist - Deep Cut (Official Video)"
- **THEN** the stored track is "Deep Cut" by "Some Artist", and the listen keeps the original title and the origin URL

### Requirement: Import never calls MusicBrainz per listen
The import SHALL use only identifiers already present in the ListenBrainz record. It SHALL NOT make MusicBrainz web requests for unmapped listens.

#### Scenario: Unmapped listen
- **WHEN** 1,000 listens without a MusicBrainz mapping are imported
- **THEN** zero MusicBrainz requests are made and all 1,000 listens are stored with their ListenBrainz artist and title

### Requirement: Plays without a known release are kept
A listen whose release is unknown SHALL still be stored, against a catalog track that has no album. It SHALL NOT be dropped, and no placeholder album SHALL be invented for it.

#### Scenario: Upload with no release
- **WHEN** a listen has an artist and title but no release name
- **THEN** a listen event is stored, its track has no album, and the import counts it as `stored` rather than `skipped`

#### Scenario: Same unresolved track played twice
- **WHEN** two listens share a normalised artist and title and neither has a release or MBID
- **THEN** both listen events reference the same catalog track

### Requirement: Imports are duplicate-safe and transactional
Re-importing listens SHALL not create duplicates, and a failed import SHALL store nothing from its run. The same listen reached through ListenBrainz and Last.fm SHALL be stored once.

#### Scenario: Backfill run twice
- **WHEN** a completed backfill is run again
- **THEN** no new listen events are stored and the result reports every listen as `duplicate`

#### Scenario: Listen already imported from Last.fm
- **WHEN** a listen with the same track and played time already exists with source `lastfm`
- **THEN** the ListenBrainz import stores no second row for it

### Requirement: Every import reports what it did
Each import result SHALL report counts of listens `fetched`, `stored`, `duplicate` and `skipped`, the reason for each skipped listen (`missing_metadata`), the number of listens stored without a release, the number of API requests made, and the time range covered. Counts SHALL be exact, never estimated.

#### Scenario: Result after a backfill
- **WHEN** a backfill fetches 2,500 listens of which 2,480 are stored, 15 are duplicates and 5 lack an artist or title
- **THEN** the result reports `fetched: 2500`, `stored: 2480`, `duplicate: 15`, `skipped: 5` with reason `missing_metadata`, the request count and the earliest and latest played times

### Requirement: Import is operator-started and rate-respecting
Backfills and syncs SHALL be queued by the operator command or a persisted schedule the operator enables, never by a web page or bot command. The client SHALL honour ListenBrainz's rate-limit headers by waiting until the reset time when the remaining allowance is exhausted.

#### Scenario: Rate limit reached
- **WHEN** a listens response reports zero remaining requests with a reset 5 seconds away
- **THEN** the next request is made no sooner than 5 seconds later and the import still completes

#### Scenario: No implicit import
- **WHEN** a user links a ListenBrainz account
- **THEN** no import job is queued until the operator starts one or enables the schedule
