# Spec Delta

## Purpose

Gives a signed-in listener a journey page that shows their analyzed listening over time, with gaps, candidate shifts and the tracks behind them, using only values the API returned.

## ADDED Requirements

### Requirement: The journey shows segments, gaps and history range
`/listening/journey` SHALL show the imported history range, each segment with its dates, and each gap with its dates and a text reason, drawn as missing history and not as silence or zero. It SHALL show the timezone and link to coverage details.

#### Scenario: Gap rendered
- **WHEN** the API returns segments 2019 to 2021 and 2024 to 2026 with a `not_imported` gap
- **THEN** the page shows the gap labelled "history not imported" between the two segments, with no line or value drawn across it

### Requirement: Candidate shifts are presented as hypotheses
Each candidate shift SHALL be labelled "an estimated change in your analyzed listening" with its date, stability and method, and a control to review its tracks. The page SHALL NOT name eras with generated labels or attach life events, moods, causes or personality.

#### Scenario: Review tracks
- **WHEN** the user selects "Review tracks" on a candidate
- **THEN** the page lists the tracks with before and after play counts and the usable-audio sample on each side

#### Scenario: No causal wording
- **WHEN** any candidate is rendered
- **THEN** its text contains the fixed hypothesis label and no cause, feeling or life-event wording

### Requirement: Periods can be compared
The page SHALL let the user pick an earlier and a later period and show each period's most-played tracks and sample size from the API. A period that is a gap or `insufficient_history` SHALL be shown as such, with no tracks.

#### Scenario: Compare two eras
- **WHEN** the user picks the 2019 era and the 2024 era
- **THEN** both lists of most-played tracks are shown with play counts and each era's usable-audio sample

### Requirement: Validation status is visible
While the API reports `validation: gate_pending`, the page SHALL show that the analysis is unvalidated. When it reports `rejected`, the page SHALL show that the journey is not available and SHALL render no candidates.

#### Scenario: Unvalidated
- **WHEN** the API returns candidates with `validation: gate_pending`
- **THEN** an "unvalidated" notice is shown above the timeline

#### Scenario: Rejected
- **WHEN** the API returns `rejected`
- **THEN** the page states the journey is not available and shows no candidates

### Requirement: Unavailable states are explicit
The page SHALL show distinct messages for `timezone_missing` (with a link to settings), `not_computed`, `stale_model`, `insufficient_history` and an unreachable API, and SHALL render no timeline values in those states.

#### Scenario: API down
- **WHEN** the eras API is unreachable
- **THEN** the page states the journey is unavailable and renders no timeline

#### Scenario: Timezone missing
- **WHEN** the API returns `timezone_missing`
- **THEN** the page asks the user to set a timezone and links to settings

### Requirement: The page is owner-only and accessible
Only the signed-in user's own journey SHALL be shown; signed-out visitors SHALL get a sign-in prompt preserving the path. Segments, gaps and candidates SHALL also be available as a keyboard-reachable list with text labels, not only as a drawing, and states SHALL NOT be shown by color alone.

#### Scenario: Signed out
- **WHEN** a signed-out visitor opens `/listening/journey`
- **THEN** they are prompted to sign in and returned to `/listening/journey` afterwards

#### Scenario: Text alternative
- **WHEN** the timeline is rendered
- **THEN** a list gives each segment, gap and candidate with dates and labels in text
