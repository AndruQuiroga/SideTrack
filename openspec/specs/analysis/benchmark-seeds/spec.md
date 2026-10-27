# analysis/benchmark-seeds Specification

## Purpose
Defines how the audio lab builds benchmark seed lists and their labels: from the owner's ListenBrainz history and from public genre charts. It covers cleaning, balance, labels and co-listening pairs, and keeping personal data out of the repo.

## Requirements

### Requirement: Personal seeds exclude non-music
`audio-lab seeds` SHALL read a ListenBrainz export and SHALL NOT select a listen as a seed if:
- its duration is longer than 10 minutes
- its artist is a known non-music pseudo-artist
- its title matches a podcast or series pattern

It SHALL report how many listens each rule excluded.

#### Scenario: Podcast episode
- **WHEN** the export contains a 55-minute listen titled "The Best in Jest"
- **THEN** no seed is written for it, and the report counts it under the duration rule

#### Scenario: YouTube Labs
- **WHEN** a listen's artist is "A YouTube Labs experiment"
- **THEN** no seed is written for it

### Requirement: Uploader-channel listens resolve to the real artist
For a listen without a MusicBrainz mapping whose title has the form "Artist - Title", `audio-lab seeds` SHALL use the parsed artist and title instead of the uploader name. The original uploader is not a credited artist.

#### Scenario: Channel upload
- **WHEN** a listen has artist "AirwaveMusicTV", title "Dabin - Alive" and no MusicBrainz mapping
- **THEN** it is counted toward the seed with artist "Dabin" and title "Alive"

#### Scenario: Mapped listen keeps its mapping
- **WHEN** a listen has a MusicBrainz mapping
- **THEN** the mapped artist and recording name are used, even when the title contains " - "

### Requirement: Personal seeds are balanced
`audio-lab seeds --count N` SHALL select N seeds:
- spread across the years in the export and across play-count bands
- with at most two seeds per primary artist
- including both tracks of the most strongly co-listened pairs, up to a configured share of N

Given the same export and options, it SHALL write the same seeds.

#### Scenario: Artist cap
- **WHEN** one artist has 50 eligible tracks
- **THEN** at most 2 of them are seeds

#### Scenario: Years covered
- **WHEN** the export has eligible listens in 2020 and 2026 and N is large enough
- **THEN** the seeds include tracks first played in each of those years

#### Scenario: Deterministic
- **WHEN** `audio-lab seeds` runs twice on the same export with the same options
- **THEN** both runs write identical files

### Requirement: Co-listening pairs are recorded
`audio-lab seeds` SHALL write `colisten.csv` with each pair of seed tracks played adjacently, and the number of distinct listening sessions in which that happened. A session ends after 30 minutes without a listen. Night sessions SHALL NOT count, because they are unattended autoplay. It SHALL include only pairs seen in at least the configured minimum of sessions (default 3).

#### Scenario: Repeated pair
- **WHEN** tracks A and B are played back to back in 4 separate sessions, and both are seeds
- **THEN** `colisten.csv` lists A and B with 4 sessions

#### Scenario: Night autoplay ignored
- **WHEN** tracks A and D are adjacent in 5 sessions, all of them night sessions
- **THEN** `colisten.csv` does not list them

#### Scenario: One-off autoplay pair
- **WHEN** tracks A and C are adjacent in only 1 session
- **THEN** `colisten.csv` does not list them

### Requirement: Sleep tracks are labelled from night sessions
A **night session** is a listening session that:
- starts between 22:00 and 04:00 local time
- lasts at least one hour
- has at least 12 listens

`audio-lab seeds` SHALL label a seed `sleep` when at least 2 of its plays, and at least 75% of them, fall in night sessions. Every other personal seed SHALL get the label `personal`.

#### Scenario: Played only while falling asleep
- **WHEN** a track has 3 plays, all inside night sessions
- **THEN** it is labelled `sleep`

#### Scenario: Daytime favourite also heard at night
- **WHEN** a track has 10 plays and 2 of them are in night sessions
- **THEN** it is labelled `personal`

### Requirement: Genre control seeds come from public charts
`audio-lab control-seeds` SHALL write seeds and `genre:<name>` labels for up to the configured number of tracks from each Deezer genre chart. It SHALL skip the "All" chart, and skip any track already present in another genre's list. It SHALL record each seed's Deezer track ID. If Deezer is unreachable, it SHALL fail with an error and write no files.

#### Scenario: Two genres
- **WHEN** the charts for Rock and Jazz each return 12 tracks and the limit is 10
- **THEN** 20 seeds are written, 10 labelled `genre:Rock` and 10 labelled `genre:Jazz`, each with a Deezer ID

#### Scenario: Deezer down
- **WHEN** the Deezer API returns an error
- **THEN** the command exits non-zero and no seed or label file exists

### Requirement: Personal data stays outside the repo
`audio-lab seeds` SHALL refuse to write its outputs to a path inside the repository working tree. Tests SHALL use synthetic exports only.

#### Scenario: Output inside the repo
- **WHEN** `--out` points inside the git working tree
- **THEN** the command exits non-zero and writes nothing
