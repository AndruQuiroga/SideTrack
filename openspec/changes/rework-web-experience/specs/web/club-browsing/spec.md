# Spec Delta

## Purpose

Lets club members find the latest scheduled week, browse past winners, and read album context and member ratings without losing their place.

## ADDED Requirements

### Requirement: Current week selection is deterministic
`/club/current` SHALL display the first week ordered by descending week number, null numbers last, then descending creation timestamp, then ascending ID. It SHALL label the result Latest scheduled week and show stored dates with an explicit timezone. It SHALL NOT imply phase enforcement or permission to participate from the clock alone.

#### Scenario: Scheduled future week
- **WHEN** the API returns weeks numbered 7 and 8, with week 8 scheduled for the future
- **THEN** Latest scheduled week links to week 8 and shows its scheduled date rather than claiming voting is open

#### Scenario: No scheduled weeks
- **WHEN** the API returns an empty week collection
- **THEN** the page says no weeks have been scheduled and shows no album, deadline, or participation action

### Requirement: Archive view state survives navigation
The archive SHALL support text search, one metadata tag filter, newest or highest-rated sort, and grid or list view. Its URL SHALL encode non-default `q`, `tag`, `sort`, and `view` values. Opening a result and returning SHALL restore that state. Unknown values SHALL use safe defaults without failing the page.

#### Scenario: Share a filtered archive
- **WHEN** a member opens `/club?q=ambient&sort=rating&view=list`
- **THEN** search shows ambient, the highest-rated sort is selected, and matching weeks appear as rows
- **AND** opening a week and returning restores the same query, sort, and view

#### Scenario: No matches
- **WHEN** filters match no archive weeks
- **THEN** the archive says no weeks match and offers Clear filters, without claiming that the entire archive is empty

### Requirement: Featured archive winner keeps chronological meaning
The latest-winner feature SHALL be selected independently of archive filters and rating sort, using descending discussion timestamp with creation timestamp as fallback, then descending creation timestamp and ascending ID. Highest-rated ordering SHALL put unrated weeks after rated weeks and show missing averages as missing, not zero.

#### Scenario: Rating sort does not replace the newest winner
- **WHEN** an older week has a higher rating than the newest winner and the member selects Highest rated
- **THEN** the older week appears first in results while Latest winner continues to identify the chronological newest winner

### Requirement: Album identity follows the stored winner
Winner titles, artists, and covers SHALL resolve from `winner_album_id` and catalog metadata. Nomination ordering and free-text pitches SHALL NOT establish winner identity. Missing winner IDs SHALL show Winner pending; unavailable catalog metadata SHALL show Album details unavailable without disguising a pitch as a title.

#### Scenario: Winner is not the first nomination
- **WHEN** a week's winner album belongs to its second nomination
- **THEN** overview, archive, and detail identify that album as the winner

#### Scenario: Winner has no artwork
- **WHEN** winner metadata loads without an image URL
- **THEN** the album title and artist remain visible and the cover area explicitly says Artwork unavailable

### Requirement: Week detail prioritizes album and discussion
Week detail SHALL present album identity, week label, stored schedule, available Discord destinations, rating average with count, member reviews, and nomination results in that reading order. Only existing Discord thread URLs SHALL be actionable. Web nomination, ballot, and rating submission controls SHALL NOT be offered in this release.

#### Scenario: Available discussion destination
- **WHEN** a stored week has a ratings thread and a configured guild ID
- **THEN** an Open ratings in Discord link targets that thread
- **AND** no web rating submission control is shown

#### Scenario: No discussion destination
- **WHEN** no relevant Discord thread or guild ID exists
- **THEN** the page states that the discussion link is unavailable and renders no fabricated link

### Requirement: Optional detail failures remain distinguishable
Failure to load rating entries, their summary, or catalog metadata SHALL mark that section unavailable without hiding successful week data. A successful empty ratings response SHALL say No ratings yet. A missing histogram SHALL say Distribution unavailable unless the summary explicitly reports zero ratings.

#### Scenario: Ratings request fails
- **WHEN** week details load but fetching ratings fails
- **THEN** the week remains visible and the reviews section says Ratings unavailable rather than No ratings yet
