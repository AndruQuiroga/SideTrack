# Spec Delta

## Purpose

Preserve historical Singles Night song sessions and participants' phase-specific ratings independently of album-club weeks, and let authorized club members browse the recovered records.

## ADDED Requirements

### Requirement: Singles Night sessions have independent identity
A Singles Night session SHALL have a stable source-thread identity, its own optional week number, original label and reviewed event date. It MUST NOT create or replace an album-club week with the same number. The displayed date SHALL reflect reviewed corrections and an explicit timezone when a time is available.

#### Scenario: Overlapping week numbers
- **WHEN** album week 1 and Singles Night week 1 are imported
- **THEN** two distinct event records exist and each retains its own source, date and numbering

#### Scenario: Calendar date without a time
- **WHEN** a source establishes a session date but no event time
- **THEN** the archive shows that date without inventing a start time

### Requirement: Song records preserve observed identity without fake albums
Sessions SHALL retain reviewed song title, artist, supplied links, ordering and submission attribution where supported by the source. Catalog linkage SHALL be optional and require a verified existing track. Missing album or catalog metadata MUST NOT cause creation of a placeholder album or fabricated track metadata.

#### Scenario: Song has no identified album
- **WHEN** a source identifies a song and artist but does not identify its album
- **THEN** the song is readable from the Singles Night session without a newly invented album or catalog track

#### Scenario: Curated heading names another participant
- **WHEN** a message heading names a submitter different from its author
- **THEN** the submission uses an explicit reviewed Discord identity mapping or remains unresolved; the curator is not automatically assigned as submitter

### Requirement: Ratings preserve song and phase attribution
A Singles Night rating SHALL identify its session, song, author and either first-listen or final phase, with a source-backed 1–5 value and optional review. A missing final rating SHALL remain missing. Bare stars or message ordering alone MUST NOT establish an uncertain song, author or phase; conflicts SHALL require reviewed mapping or exclusion.

#### Scenario: First and final ratings differ
- **WHEN** one participant rates the same song 3.5 on first listen and 4.0 at the end
- **THEN** both distinct ratings are stored and displayed under their respective phases

#### Scenario: Unknown phase
- **WHEN** a star-only reply has no unambiguous phase evidence and no reviewed assignment
- **THEN** it is listed as unresolved in preview and does not silently become a final rating

### Requirement: Singles Night reads follow club access boundaries
Singles Night list and detail API reads SHALL require club membership or the authorized bot acting as itself. Web reads SHALL use server-held credentials and the session-derived actor. Anonymous visitors SHALL see a sign-in prompt; signed-in non-members SHALL see an access denial. Normal members SHALL have no Singles Night mutation endpoint.

#### Scenario: Anonymous and non-member reads
- **WHEN** anonymous and authenticated non-member callers request Singles Night records
- **THEN** the API rejects access and the corresponding web pages respectively show sign-in and members-only notices without source data

#### Scenario: Member reads imported session
- **WHEN** a member opens a stored Singles Night session
- **THEN** the read succeeds using their server session and exposes structured session data without raw exports or operator-only import metadata

### Requirement: Club navigation exposes a read-only Singles Night archive
Club navigation SHALL link to a Singles Night archive separate from the album archive. Its list SHALL order sessions by reviewed event date descending with stable ties; details SHALL show source-backed songs, submitters and distinct rating phases. Empty results, missing fields, failed reads and absent ratings SHALL remain distinguishable. No playback, download or participation controls SHALL be introduced.

#### Scenario: Browse imported Singles Night
- **WHEN** a member follows the Singles Night link from Club and opens a listed session
- **THEN** its reviewed date, available songs and first/final rating sections are visible and an existing source thread can be opened in Discord

#### Scenario: No final ratings or failed reads
- **WHEN** a session loads with first-listen ratings but no final ratings, or its rating read fails
- **THEN** final ratings are shown as absent in the first case and unavailable in the second, without fabricated scores

### Requirement: Participant deletion preserves other participants' history
Account deletion SHALL remove the participant's submission attribution, ratings and reviews from Singles Night. Neutral session/song identities and other participants' contributions SHALL remain readable. Import replay MUST NOT restore erased contributions or leave deleted names in public provenance fields.

#### Scenario: One participant deletes their account
- **WHEN** a participant with submissions and ratings is deleted from a session shared with another participant
- **THEN** the deleted participant's attributed contributions disappear, the other participant's ratings remain, and replay of the same import does not recreate the erased contributions
