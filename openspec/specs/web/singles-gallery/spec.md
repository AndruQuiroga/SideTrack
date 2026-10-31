# web/singles-gallery Specification

## Purpose
Let club members browse the music submitted across Singles Night sessions directly on the landing page, with artwork and music identity leading and listener impressions available inline.

## Requirements

### Requirement: The landing page exposes songs without opening nights
The Singles Night home page SHALL show song cards grouped by night, newest first, with no night-selection or detail-page navigation required to see the initial songs. Within each night it SHALL preserve submission order and distinct session/song identities. Existing night detail URLs SHALL remain available as secondary links.

#### Scenario: Current seven-night archive
- **WHEN** an authorized member opens `/club/singles` with seven available nights containing 44 songs
- **THEN** all seven night headings and their 44 song cards are present in the initial gallery without opening any night

#### Scenario: Repeat song across nights
- **WHEN** the same music title appears in two nights
- **THEN** both submissions remain in their respective night groups with their own ratings and submitters

### Requirement: Song identity and artwork lead each card
Cards SHALL prioritize square artwork, song title and artist, followed by submitter and a compact labeled rating summary. Every card SHALL retain readable identity when artwork is missing or fails. Missing attribution SHALL be explicit. Source and music-provider links SHALL remain accessible without treating an external link as an in-app player.

#### Scenario: Missing image and deleted submitter
- **WHEN** a song has no usable artwork and its submitter is absent
- **THEN** its title and artist remain visible alongside Artwork unavailable and Submitter unavailable

### Requirement: Listener impressions expand on the home page
Members SHALL be able to expand and collapse each song's individual ratings and reviews on the home page without navigating away. First-listen and final phases SHALL remain distinct. Final-rating sections SHALL be omitted when no final ratings exist; absent first-listen ratings SHALL be labeled as unrated rather than zero.

#### Scenario: Historical first-listen-only song
- **WHEN** a member expands a song with first-listen ratings and no final ratings
- **THEN** its listener names, precise scores and available reviews appear inline and no empty final-rating column is rendered

#### Scenario: Both rating phases exist
- **WHEN** a song contains both phases
- **THEN** each phase is explicitly labeled and its individual ratings remain separate

### Requirement: Older nights load in place with bounded requests
The gallery SHALL load at most eight nights per batch and at most three concurrent detail requests. When more nights exist, an accessible older-nights action SHALL append their song groups to the same home page, preserving visible groups and expanded impressions. Failed loads SHALL offer a real retry without duplicate groups.

#### Scenario: More than eight nights
- **WHEN** a member loads an archive containing more than eight nights and activates Show older nights
- **THEN** the next batch appends on `/club/singles`, earlier songs remain visible, and no individual night page is required

#### Scenario: Failed older batch
- **WHEN** loading an older batch fails and is retried
- **THEN** already loaded nights remain intact and each successfully loaded night appears once

### Requirement: Access and partial failures remain honest
The gallery SHALL preserve server-session-derived identity, member-only access and credential boundaries. A failed night detail request SHALL show a localized unavailable state without inventing songs or concealing available nights. Authentication and access failures SHALL display the appropriate global access state rather than cached private content or an empty gallery.

#### Scenario: One night unavailable
- **WHEN** the night index succeeds but one detail request fails temporarily
- **THEN** other loaded nights display normally and the affected group offers a retry with an unavailable message

#### Scenario: Session or membership lost during load
- **WHEN** an older-batch or retry request discovers missing authentication or club membership
- **THEN** the gallery displays the applicable sign-in or access-denied state and reveals no additional private records

### Requirement: Gallery controls work on narrow screens and keyboards
The gallery SHALL reflow without horizontal page overflow at widths down to 320 pixels. Song-expansion and older-night controls SHALL be keyboard operable, expose expanded/loading state, retain visible focus and keep essential metadata available without hover. Artwork dimensions SHALL reserve space before loading.

#### Scenario: Narrow keyboard browsing
- **WHEN** a member uses the gallery at 320 pixels wide with keyboard navigation
- **THEN** artwork, identity, rating controls and expanded reviews remain readable without horizontal page scrolling and focus remains visible
