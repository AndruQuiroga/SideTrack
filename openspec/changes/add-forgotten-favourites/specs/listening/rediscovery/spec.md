# Spec Delta

## Purpose

Resurfaces tracks a listener played heavily in the past but not recently, using explicit play-count rules over their own imported history, with coverage checks, disclosed session exclusions and no inferred loves.

## ADDED Requirements

### Requirement: Favourite and forgotten are explicit versioned rules
A past favourite SHALL be a track with at least N included plays within some window of W consecutive days, and forgotten SHALL mean no included play in the last M days. N, W, M, K and D and the rule version SHALL be returned with every response.

#### Scenario: Track qualifies
- **WHEN** with defaults N=8, W=90, M=365 a track had 10 included plays in March 2021 and none in the last 365 days, and history checks pass
- **THEN** it is listed with its peak window, 10 peak plays and its last included play date

#### Scenario: Recently played
- **WHEN** the same track had one included play 200 days ago
- **THEN** it is not listed

### Requirement: Included plays follow effective session classification
Plays in sessions whose effective classification is autoplay SHALL be excluded by default and their count returned; the user SHALL be able to include them per request. Plays in `unknown` sessions SHALL be included and their count returned.

#### Scenario: Autoplay excluded by default
- **WHEN** a track's 9 peak plays include 3 in a `night_autoplay` session without override
- **THEN** it counts 6 included peak plays, is not listed under N=8, and the excluded autoplay count is returned

#### Scenario: Keep override counts
- **WHEN** the user set `keep` on that session
- **THEN** its 3 plays count as included and the track is listed with 9 peak plays

#### Scenario: Unknown sessions disclosed
- **WHEN** the user has no timezone and sessions are `unknown`
- **THEN** their plays are included and the response reports how many plays came from `unknown` sessions

### Requirement: Forgotten requires covered and active recent history
The list SHALL be computed only when imported coverage spans the full last M days and the user had at least K other included plays on at least D distinct days in that span. Otherwise the response SHALL be `not_imported`, `coverage_gap` or `insufficient_history` with no tracks.

#### Scenario: No import
- **WHEN** the user has no completed import
- **THEN** the response is `not_imported` with no tracks

#### Scenario: Coverage ends early
- **WHEN** imported coverage ends 200 days ago
- **THEN** the response is `coverage_gap` naming the coverage end date, with no tracks

#### Scenario: Quiet recent year
- **WHEN** coverage spans the window but the user had 30 included plays on 12 days in it, with K=50 and D=20
- **THEN** the response is `insufficient_history` with those counts and no tracks

#### Scenario: Nothing qualifies
- **WHEN** checks pass but no track meets the rules
- **THEN** the response is `none_found` with the rule values and coverage range

### Requirement: The list discloses coverage and counting limits
Every list SHALL show the imported coverage range, the rule values, the excluded autoplay count, the `unknown`-session count, and a note that versions or uploads of the same song may be counted separately.

#### Scenario: Disclosure block
- **WHEN** the list is shown
- **THEN** the coverage start and end dates, N, W, M, the excluded count and the versions note are visible

### Requirement: No loves are claimed or inferred
Responses and pages SHALL NOT describe a track as loved, liked or the user's favourite, and SHALL describe it as played a lot in its peak period; no love or like signal SHALL be stored or inferred.

#### Scenario: Wording
- **WHEN** a listed track is rendered
- **THEN** its text says it was played a lot in its peak period and contains no "loved", "liked" or "your favourite"

### Requirement: Rediscovery is owner-only
Forgotten favourites and dismissals SHALL be readable only by their owner regardless of `listening_visibility`.

#### Scenario: Other member
- **WHEN** member V requests user U's forgotten favourites
- **THEN** the API responds 404

### Requirement: Dismissals are private and deletable
The user SHALL be able to dismiss a listed track with reason `not_a_favourite` or `not_now`; dismissed tracks SHALL be hidden from the list, listed separately, removable singly or all, and deleted with the account.

#### Scenario: Dismiss and restore
- **WHEN** the user dismisses a track and later removes that dismissal
- **THEN** the track is hidden while dismissed and listed again afterwards if it still qualifies

#### Scenario: Account deletion
- **WHEN** the user's account is deleted
- **THEN** no dismissal row references that user

### Requirement: The page is metadata-only
The rediscovery page SHALL NOT play audio or link to audio files or streams.

#### Scenario: No audio
- **WHEN** the page is rendered
- **THEN** it contains no audio element and no audio file or stream link
