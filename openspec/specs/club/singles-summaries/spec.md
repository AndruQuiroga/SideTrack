# club/singles-summaries Specification

## Purpose
Provide trustworthy per-song rating summaries for Singles Night browsing while retaining the original individual ratings, rating phases, precision and club access rules.

## Requirements

### Requirement: Song summaries are computed per rating phase
Authorized Singles Night detail reads SHALL include a count and nullable arithmetic mean for each song's first-listen and final ratings, computed independently from its stored ratings. Empty phases SHALL return count zero and mean null. Summaries SHALL NOT alter, round or combine individual source ratings.

#### Scenario: First-listen ratings only
- **WHEN** a song has first-listen scores 3.5 and 4, and no final ratings
- **THEN** its first-listen summary reports count 2 and mean 3.75, its final summary reports count 0 and mean null, and individual scores remain 3.5 and 4

#### Scenario: Distinct final phase
- **WHEN** that song also has a final score of 5
- **THEN** its first-listen mean remains 3.75 and its final summary independently reports count 1 and mean 5

### Requirement: Summaries preserve identity and erasure behavior
Summary counts SHALL count rating records for the exact song/session/phase, without multiplying ratings through submission or artwork joins. Reading summaries SHALL create no writes, jobs or provider calls. Deleted ratings SHALL no longer contribute to subsequent reads, and repeated songs in different nights SHALL remain independent.

#### Scenario: Deleted participant contribution
- **WHEN** deletion removes one of a song's two ratings
- **THEN** its next detail read recomputes count and mean from only the remaining rating and creates no replacement contribution

#### Scenario: Multiple submissions and artwork
- **WHEN** a song has artwork, multiple submitters and two first-listen ratings
- **THEN** its first-listen count remains 2 and each original rating is represented once

### Requirement: Summary fields are additive and member gated
Summary fields SHALL be additive to existing Singles Night detail responses and retain current service/member authorization. Responses SHALL expose no operator receipts, provider credentials or raw import evidence. Existing song, artwork, submission and individual-rating fields SHALL remain compatible.

#### Scenario: Anonymous and non-member reads
- **WHEN** an anonymous caller or authenticated non-member requests a session with summaries
- **THEN** the existing 401 or 403 response is preserved and no summary or private session data is returned
