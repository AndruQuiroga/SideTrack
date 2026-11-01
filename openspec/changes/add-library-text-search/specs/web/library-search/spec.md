# Spec Delta

## Purpose

Gives a signed-in user a page to search their own analysed library by describing a sound, showing only API results with their coverage, model, ranking method and limits, and never playing or linking audio.

## ADDED Requirements

### Requirement: The search page shows only API results
The `/listening/search` page SHALL render only results the library-search API returned for the signed-in user. When the API request fails, the page SHALL show an unavailable state and no result list.

#### Scenario: API down
- **WHEN** the API is unreachable and the user submits a query
- **THEN** the page says search is unavailable and lists no tracks

#### Scenario: Signed out
- **WHEN** a signed-out visitor opens `/listening/search`
- **THEN** the page asks them to sign in and shows no search results

### Requirement: Each search state has its own message
The page SHALL show distinct text for `pending`, `no_confident_match`, `no_eligible_audio`, `unavailable`, `failed` and `not_evaluated`, and none of them SHALL render placeholder tracks.

#### Scenario: No confident match
- **WHEN** the API returns `no_confident_match` with 450 tracks considered
- **THEN** the page says no tracks matched closely enough among 450 eligible tracks and lists none

#### Scenario: No eligible audio
- **WHEN** the API returns `no_eligible_audio`
- **THEN** the page says none of the user's listened tracks has analysed audio yet and shows the coverage counts

#### Scenario: Not evaluated
- **WHEN** the API returns `not_evaluated`
- **THEN** the page says library search has not been enabled yet and lists no tracks

### Requirement: Pending searches wait for the encoding job
While a search is `pending`, the page SHALL say the query is being prepared, poll the job status, and render results only after the API returns them.

#### Scenario: Pending then complete
- **WHEN** the first response is `pending` and a later poll returns `ok` with 3 results
- **THEN** the page shows the preparing message and then exactly those 3 results

### Requirement: Coverage is shown beside every result list
The page SHALL show, above results or an empty state, how many of the user's listened tracks were eligible for the search and the selected full/preview filter.

#### Scenario: Coverage line
- **WHEN** the API reports 800 listened tracks and 450 eligible
- **THEN** the page states that 450 of 800 tracks have eligible audio for this search

### Requirement: Results show kind and analysed duration without scores
Each result SHALL show artist, title, whether the analysed audio is a full track or a preview, and the analysed duration. The page SHALL NOT display a similarity as a percentage, probability, confidence or match score.

#### Scenario: Preview result
- **WHEN** a result is a 30-second preview
- **THEN** its row says preview and 00:30 analysed

#### Scenario: No percentages
- **WHEN** any results are rendered
- **THEN** no result row contains a percent sign or the words probability, confidence or match score

### Requirement: The ranking explanation states the method and its limits
A "how this list was ranked" panel SHALL name the model, revision, ranking method and version and evaluation run returned by the API, and SHALL state that rewording a query can reorder results and that results describe at most the first three minutes of each track.

#### Scenario: Opening the panel
- **WHEN** the user opens the ranking explanation for a result list
- **THEN** it shows the API's model, revision, method and evaluation run, and the rewording and three-minute notes

### Requirement: Feedback controls are optional and private
Each result SHALL offer "useful" and "not relevant" controls that store the user's mark, show the stored mark, and allow removing it. The page SHALL link to export and delete the user's search history and marks.

#### Scenario: Marking not relevant
- **WHEN** the user marks a result not relevant
- **THEN** the API stores the mark and the row shows it as marked

### Requirement: The page is metadata-only
The page SHALL NOT play audio or link to audio files or streams.

#### Scenario: No audio elements
- **WHEN** a result list is rendered
- **THEN** the page contains no audio or video element and no link to an audio file path or stream URL

### Requirement: The page is usable without color or a pointer
Every control SHALL be reachable and operable by keyboard with a visible focus indicator, every state SHALL be conveyed in text, and the result list SHALL be announced to screen readers when it updates.

#### Scenario: Keyboard search
- **WHEN** a user types a query, presses Enter and tabs through results using only the keyboard
- **THEN** the search runs, each result and its feedback controls receive focus in order, and a live region announces the result count
