# Spec Delta

## Purpose

Defines how Sidetrack obtains audio for analysis: only when the owner explicitly asks, stored once by content hash on the owner's disk, checked against the track it claims to be, recorded for later analysis, and never scheduled or served.

## ADDED Requirements

### Requirement: Fetching is explicit and opt-in
Audio SHALL be fetched only by an operator running the fetch command. The command MUST refuse to fetch unless `SIDETRACK_AUDIO_FETCH_ENABLED` is `true`. No job, schedule, API route or bot command SHALL start a fetch.

#### Scenario: Fetching is disabled
- **WHEN** the operator runs the fetch command with `SIDETRACK_AUDIO_FETCH_ENABLED` unset
- **THEN** the command exits non-zero with a message naming the setting, and no file or row is created

#### Scenario: Nothing schedules a fetch
- **WHEN** the worker's registered tasks and persisted schedules are listed
- **THEN** none of them fetches audio

### Requirement: Seeds fetch full tracks and previews
For each seed row (artist, title, optional YouTube video ID, optional Deezer track ID), the fetch command SHALL try to obtain the full track from YouTube Music and the 30-second preview from Deezer, each as a separate asset. A seed with an explicit ID MUST use that ID instead of searching. A source that has no result SHALL be reported for that seed without stopping the run.

#### Scenario: Both sources found
- **WHEN** a seed for an available track is fetched
- **THEN** two assets are recorded for it, one with kind `full` and source `youtube_music`, and one with kind `preview` and source `deezer_preview`, each with its source ID

#### Scenario: Explicit video ID
- **WHEN** a seed names YouTube video ID V
- **THEN** the full asset's source ID is V and no search is made

#### Scenario: Source has no result
- **WHEN** Deezer has no preview for a seed
- **THEN** the run records the full-track asset, lists the seed as missing a preview in its summary, and continues with the next seed

### Requirement: Files are stored once by content hash
Each fetched file SHALL be stored as `<audio dir>/<sha256>.<ext>`, in its native container without transcoding. The SHA-256 MUST be unique among assets. Fetching identical bytes again SHALL reuse the existing file and row.

#### Scenario: Same audio fetched twice
- **WHEN** a seed is fetched twice and the source returns identical bytes
- **THEN** there is one file and one asset row, and the second run reports it as already stored

### Requirement: Assets are verified by fingerprint
Each asset SHALL be fingerprinted with Chromaprint and looked up on AcoustID. The asset SHALL record its verification as `confirmed` (AcoustID's best match agrees with the seed's artist and title), `mismatch` (a confident match names a different recording) or `unverified` (no confident match, or the lookup was unavailable), together with the matched recording MBID and score when there is one. A `mismatch` SHALL be kept and reported, not deleted.

#### Scenario: Matching recording
- **WHEN** AcoustID's best match for a fetched file has the seed's artist and title
- **THEN** the asset's verification is `confirmed` with that recording MBID

#### Scenario: Wrong upload
- **WHEN** AcoustID confidently matches a fetched file to a different recording
- **THEN** the asset's verification is `mismatch`, and the run summary lists it

#### Scenario: AcoustID unavailable
- **WHEN** the AcoustID lookup fails or no API key is configured
- **THEN** the asset is stored with verification `unverified`, and the run summary says how many assets were not checked

### Requirement: Assets link to the catalog when possible
The fetch command SHALL resolve each seed to a catalog track through the catalog's public interface and link its assets to it. A seed that can't be resolved SHALL still be fetched, and its assets keep the requested artist and title with no track link.

#### Scenario: Obscure track not in MusicBrainz
- **WHEN** a seed's artist and title can't be resolved to a catalog track
- **THEN** its assets are stored with no track link and with the seed's artist and title

### Requirement: The manifest exports assets for analysis
The manifest command SHALL write a CSV with one row per asset that still has a file: path relative to the audio directory, SHA-256, kind, source, source ID, duration, verification, track ID if linked, artist and title. It SHALL include only assets whose file exists on disk.

#### Scenario: Exporting
- **WHEN** the operator exports a manifest after fetching 3 seeds with both sources
- **THEN** the CSV has 6 rows whose paths resolve to existing files under the audio directory

### Requirement: Pruning removes files and keeps records
The prune command SHALL delete asset files fetched more than `SIDETRACK_AUDIO_RETENTION_DAYS` days ago. It SHALL mark those assets' file as deleted and keep their rows, so derived results keep their reference.

#### Scenario: Expired file
- **WHEN** retention is 30 days and an asset was fetched 31 days ago
- **THEN** prune deletes its file, the row remains with a deletion time, and the manifest no longer lists it

### Requirement: Audio is never served and credentials never recorded
No API route or web page SHALL return audio bytes, audio file paths or the audio directory. The YouTube cookie file's path and contents MUST NOT appear in logs, asset rows, the manifest or command output.

#### Scenario: API surface
- **WHEN** the API's registered routes and OpenAPI schema are inspected
- **THEN** no route serves audio assets, and no response schema contains an asset path field

#### Scenario: Fetch with cookies
- **WHEN** the operator fetches with a cookie file
- **THEN** the captured logs, the stored rows and the printed summary do not contain the cookie file's path or any line from it
