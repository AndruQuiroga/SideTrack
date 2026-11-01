# Spec Delta

## Purpose

Builds an ordered, metadata-only sequence of a listener's own tracks that moves from one chosen track toward another in embedding space, with a closeness versus exploration control, honest explanations and explicit insufficient states.

## ADDED Requirements

### Requirement: Bridges use only the requester's eligible library
A bridge SHALL be built only from tracks in the requesting user's listening history whose `audio_for_track` status is `ok` for the current model revision. Endpoints outside that library SHALL respond 404. Ambiguous links SHALL never be used as endpoints or steps.

#### Scenario: Foreign endpoint
- **WHEN** a user requests a bridge whose end track is not in their listening history
- **THEN** the API responds 404 and builds nothing

#### Scenario: Ambiguous endpoint
- **WHEN** the start track's audio status is `ambiguous`
- **THEN** the API returns `endpoint_ambiguous` and no steps

#### Scenario: Steps stay in library
- **WHEN** a bridge is built
- **THEN** every step is a distinct track from the user's eligible library

### Requirement: Endpoints must be embedded
When an endpoint has no audio or no current embedding the API SHALL return `endpoint_not_embedded` naming the endpoint, and when an endpoint is missing from the request it SHALL return `missing_endpoint`; neither SHALL return steps.

#### Scenario: Endpoint without embedding
- **WHEN** the end track's status is `no_embedding`
- **THEN** the response is `endpoint_not_embedded` for the end track with no steps

### Requirement: Steps are selected by waypoint similarity with MMR
For a length n from 3 to 12 the system SHALL interpolate n waypoints between the endpoint vectors in the original space, and for each waypoint in order select the unused eligible track maximising lambda times cosine to the waypoint minus (1 minus lambda) times maximum cosine to already selected steps, where lambda comes from the closeness setting.

#### Scenario: Length honoured
- **WHEN** a user requests 6 steps and the library has enough candidates
- **THEN** the response has exactly 6 steps between the endpoints, with no track repeated and neither endpoint's track among them

#### Scenario: Closer versus exploratory
- **WHEN** the same endpoints are requested with the closest setting and with the most exploratory setting
- **THEN** the mean pairwise cosine among steps is not lower for the closest setting than for the exploratory one

#### Scenario: Out-of-range length
- **WHEN** a user requests 20 steps
- **THEN** the API responds 422

### Requirement: Bridges are deterministic and versioned
The same endpoints, length, setting, eligible library, model revision and method version SHALL produce the same ordered steps, and the response SHALL include the model, revision and method version.

#### Scenario: Repeat request
- **WHEN** a user requests the same bridge twice without library or model changes
- **THEN** both responses list identical steps and versions

### Requirement: Small libraries report insufficient candidates
When fewer eligible tracks than requested steps remain after excluding endpoints, the API SHALL return `insufficient_candidates` with the eligible count and requested length and no partial bridge.

#### Scenario: Tiny library
- **WHEN** a user with 5 eligible tracks requests 6 steps
- **THEN** the response is `insufficient_candidates` reporting 3 available candidates and 6 requested

### Requirement: Responses are metadata-only
Bridge responses and pages SHALL contain only track metadata, step order, similarities and versions, and SHALL NOT contain audio URLs, file paths, stream links or playable media.

#### Scenario: No audio in response
- **WHEN** a bridge response is returned
- **THEN** no field contains a file path, an audio URL or a stream link, and the page renders no audio element

### Requirement: Explanations avoid quality claims
Each step SHALL show its similarity to the previous step and to the end track as labelled cosine or rank, not as a percentage, probability or quality score, and every bridge SHALL state that the method ignores tempo, key, lyrics and mixability and covers at most the first three minutes.

#### Scenario: Step explanation
- **WHEN** the user expands a step
- **THEN** it shows "similarity to previous" and "similarity to end" without a percent sign and the method note is visible

### Requirement: Bridges are labelled experimental until evaluated
Until an owner evaluation comparing bridges with plain nearest-neighbour lists and a random control is recorded and accepted for the current method version, responses SHALL carry `not_evaluated` and the page SHALL label the bridge as an experiment.

#### Scenario: No accepted evaluation
- **WHEN** no accepted evaluation exists for the method version
- **THEN** the response status includes `not_evaluated` and the page shows an experiment notice

### Requirement: Users can edit and save bridges privately
The user SHALL be able to remove a step, replace it with the next MMR candidate, reorder steps and save the list. Saved bridges SHALL be visible only to their owner, deletable singly, and deleted with the account.

#### Scenario: Replace a step
- **WHEN** the user replaces step 3
- **THEN** step 3 becomes the next-best unused candidate for that waypoint and other steps are unchanged

#### Scenario: Private saved bridge
- **WHEN** member V requests user U's saved bridge
- **THEN** the API responds 404

#### Scenario: Account deletion
- **WHEN** the owner's account is deleted
- **THEN** no saved bridge row references that user
