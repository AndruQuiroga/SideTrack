# Spec Delta

## Purpose

Lets a user search their own analysed library by describing a sound in words, using the joint audio/text model, with evaluated ranking, abstention, visible coverage and provenance, and private, deletable query history.

## ADDED Requirements

### Requirement: Search is limited to the acting user's eligible library
A library search SHALL rank only tracks the acting user has listened to whose representative audio has a current embedding of the search model, revision and pipeline. A request for another user's library SHALL respond 404 and enqueue nothing.

#### Scenario: Own library only
- **WHEN** user U searches and user V has listened to an embedded track U has never played
- **THEN** that track is absent from U's results

#### Scenario: Searching someone else's library
- **WHEN** user U requests a search of user V's library
- **THEN** the API responds 404 and no encoding job is queued

#### Scenario: One result per track
- **WHEN** a listened track has both a full-track asset and a preview asset embedded
- **THEN** the track appears at most once in the results, represented by its preferred asset

### Requirement: Query text is validated
A query SHALL be 1 to 200 characters after trimming whitespace. Any other query SHALL be rejected with 422 and SHALL NOT be stored or encoded.

#### Scenario: Empty query
- **WHEN** a user submits a query of only spaces
- **THEN** the API responds 422 and no query row or job exists

#### Scenario: Over-long query
- **WHEN** a user submits a 201-character query
- **THEN** the API responds 422 and no query row or job exists

### Requirement: Queries are encoded in the same model space as the audio
A query SHALL be encoded by the text tower of the same model and checkpoint revision as the audio embeddings it is compared with, and SHALL be compared only with embeddings of that model, revision and pipeline. Each stored query vector SHALL record its model, revision and dimension.

#### Scenario: Matching revision
- **WHEN** a query is encoded with MuQ-MuLan at the enabled revision
- **THEN** the stored query vector has 512 dimensions, unit length and that revision

#### Scenario: Older audio revision ignored
- **WHEN** the library holds embeddings for an older checkpoint revision as well as the current one
- **THEN** only assets with current-revision embeddings are ranked

### Requirement: Query encoding runs only on the GPU queue
Encoding a new query SHALL happen in a job on the `gpu` queue. The API process SHALL NOT load the model. Until the job finishes, the search SHALL report `pending` with its job ID and return no results.

#### Scenario: New query
- **WHEN** a user submits a query they have not searched before
- **THEN** the API responds 202 with status `pending` and a job ID, one encoding job is on the `gpu` queue, and no results are returned

#### Scenario: CPU worker only
- **WHEN** an encoding job is queued and only a CPU worker is running
- **THEN** the job stays queued and the search stays `pending`

### Requirement: Repeated queries reuse the stored encoding
When the acting user already has a stored encoding of the same normalised query text for the current model revision, the search SHALL rank immediately from it and SHALL NOT queue a job.

#### Scenario: Repeat search
- **WHEN** a user repeats a query whose encoding is stored for the current revision
- **THEN** results are returned in the same response and no job is queued

#### Scenario: Revision changed
- **WHEN** the stored encoding has an older revision than the enabled model
- **THEN** the search is `pending` and a new encoding job is queued

### Requirement: Unavailable encoding is reported, never substituted
When the text tower, its libraries or CUDA cannot be loaded, the encoding job SHALL fail with `unavailable`, store no vector, and the search SHALL report `unavailable` with no results. No path SHALL substitute a vocabulary term, metadata match or other query.

#### Scenario: GPU worker without CUDA
- **WHEN** an encoding job runs where CUDA is unavailable
- **THEN** the job fails with `unavailable`, no query vector is stored and the search reports `unavailable` with an empty result list

#### Scenario: Other failure
- **WHEN** an encoding job fails for a reason other than availability
- **THEN** the search reports `failed` and no results

### Requirement: Search requires an accepted evaluation
The search SHALL rank only with a ranking configuration (method, version, abstention threshold and evaluation run) that the owner has recorded as accepted. Without one, every search SHALL report `not_evaluated`, queue nothing and return no results.

#### Scenario: No accepted configuration
- **WHEN** no accepted ranking configuration is recorded and a user searches
- **THEN** the response status is `not_evaluated`, no job is queued and no results are returned

#### Scenario: Accepted configuration
- **WHEN** an accepted configuration is recorded
- **THEN** every response names its method, version and evaluation run

### Requirement: Results abstain below the accepted threshold
The search SHALL return only tracks whose score meets the accepted abstention threshold, at most the requested number (default 20, maximum 50), best first. When no track meets it, the status SHALL be `no_confident_match` with an empty list and the number of tracks considered.

#### Scenario: Nothing meets the threshold
- **WHEN** 450 tracks are eligible and none scores at or above the threshold
- **THEN** the status is `no_confident_match`, the list is empty and the response reports 450 tracks considered

#### Scenario: Some results
- **WHEN** 3 eligible tracks meet the threshold and 20 are requested
- **THEN** exactly those 3 are returned in descending score order

### Requirement: Results carry provenance, not probabilities
Each response SHALL include the model, revision, pipeline, ranking method and version; each result SHALL include track identity, asset kind (full or preview) and analysed duration, or that it is unknown. No field SHALL present a score as a percentage, probability or confidence.

#### Scenario: Full track longer than the cap
- **WHEN** a result's full-track asset is 312 seconds long
- **THEN** its analysed duration is 180 seconds and its kind is `full`

#### Scenario: No probability fields
- **WHEN** any search response is serialised
- **THEN** it contains no field named or described as probability, confidence or percent match

### Requirement: Coverage is reported with every search
Every search response, including empty and unavailable ones, SHALL report the number of distinct tracks in the user's listening history, how many are eligible for this model and filter, and how many are excluded, split by reason `no_link`, `ambiguous` or `no_embedding`. A track whose audio link is ambiguous SHALL NOT be ranked.

#### Scenario: Partial coverage
- **WHEN** a user has listened to 800 distinct tracks, 450 of them eligible
- **THEN** the response reports 800 listened, 450 eligible and 350 excluded split by reason

#### Scenario: Ambiguous link excluded
- **WHEN** a listened track's only audio link is flagged ambiguous
- **THEN** the track is not among the results and is counted under `ambiguous`

#### Scenario: No eligible audio
- **WHEN** none of the user's listened tracks is eligible
- **THEN** the status is `no_eligible_audio`, no job is queued and the coverage counts are returned

### Requirement: Users can filter full tracks and previews
The search SHALL accept filters to include full-track assets, previews or both (default both), and coverage SHALL be computed for the selected filter.

#### Scenario: Full tracks only
- **WHEN** a user searches with previews excluded
- **THEN** no result has kind `preview` and the eligible count excludes preview-only tracks

### Requirement: Query history is private and deletable
Stored queries and their encodings SHALL be readable only by their user. The user SHALL be able to list, export as JSON and delete them, singly or all; deleting a user SHALL delete them.

#### Scenario: Another user reads history
- **WHEN** user U requests user V's search history
- **THEN** the API responds 404

#### Scenario: Clearing history
- **WHEN** a user deletes all of their search history
- **THEN** none of their query rows or query vectors remain and a repeat of an old query queues a new encoding job

#### Scenario: Account deleted
- **WHEN** a user with stored queries and feedback is deleted
- **THEN** none of their query, vector or feedback rows remain

### Requirement: Result feedback is optional, private and exportable
A user SHALL be able to mark a result `useful` or `not_relevant` for a query, change or remove the mark, and export or delete all marks. Marks SHALL be visible only to that user and SHALL NOT change any other user's results or retrain any model.

#### Scenario: Marking a result
- **WHEN** a user marks a result `not_relevant` and repeats the search
- **THEN** the result carries the user's `not_relevant` mark

#### Scenario: Export
- **WHEN** a user exports their search data
- **THEN** the JSON contains each stored query text, its model revision and timestamps, and each mark, and contains no other user's data
