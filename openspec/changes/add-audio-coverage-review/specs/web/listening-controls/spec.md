# Spec Delta

## Purpose

Gives a signed-in listener one page showing what their audio-derived results rest on,
with the controls to review excluded sessions and ambiguous or missing audio links, using only
values the API returned.

## ADDED Requirements

### Requirement: The coverage page shows the API's buckets exactly
`/listening/coverage` SHALL show, for the selected period and facet, total, excluded and included plays and the four coverage buckets exactly as the API returned them, with a visible statement that the buckets sum to included plays. It SHALL show the period's time zone.

#### Scenario: Mockup week rendered
- **WHEN** the API returns included 84 with buckets 45, 16, 9 and 14 and 6 excluded plays
- **THEN** the page shows 45, 16, 9 and 14, "84 included plays", and "6 plays in excluded sessions"

### Requirement: Facets are selected and stated
The page SHALL show which facet the counts describe, let the user switch facet, and show each facet's model, checkpoint revision, pipeline and evaluation gate status. A facet reported `facet_unavailable` SHALL be shown as "not available yet" with no counts.

#### Scenario: Mood not available
- **WHEN** the user selects `mood` and the API reports `facet_unavailable`
- **THEN** the page says mood analysis is not available yet and renders no bucket numbers

### Requirement: Analysis states are distinct and not color-only
Track lists SHALL label each state (`no audio`, `ambiguous link`, `file missing`, `not computed`, `stale model`, `analysis failed` with its reason, `insufficient sample`) in text, distinguishable without color, and SHALL show full or preview and analyzed duration for usable tracks.

#### Scenario: Failed track
- **WHEN** a listed track has state `failed` with reason `decode_failed`
- **THEN** its row reads "analysis failed: decode_failed" in text

#### Scenario: Partial analysis
- **WHEN** a usable track's full asset is 312 s with 180 s analyzed
- **THEN** its row reads "full, first 03:00 of 05:12 analyzed"

### Requirement: Sessions can be reviewed and overridden
The page SHALL list `night_autoplay`, `unclassified`, `unknown` and overridden sessions with time, length, listen count, rule kind, override and `effective_kind`, and let the user set or clear a `keep` or `autoplay` override. After an override succeeds, the page SHALL show counts refreshed from the API.

#### Scenario: Re-include a session
- **WHEN** the user sets `keep` on a 14-play `night_autoplay` session and the API confirms
- **THEN** the page shows the session as "kept (your choice)" and the included plays from the refreshed report

#### Scenario: Override fails
- **WHEN** the override request fails
- **THEN** the page shows an error, keeps the previous classification and counts, and does not show the new state

### Requirement: Links can be reviewed and corrected
The page SHALL list tracks whose audio status is `no_audio` or `ambiguous` with play counts, candidate links, method, confidence, `ambiguous` flag and evidence, and SHALL offer confirm and reject only to users with the resolution operator permission. It SHALL NOT offer similarity-derived candidates or describe similarity as proof of a match.

#### Scenario: Confirm a candidate
- **WHEN** an operator confirms a candidate link and the API accepts it
- **THEN** the track leaves the review list and the counts are refreshed from the API

#### Scenario: Non-operator sees evidence only
- **WHEN** a user without operator permission opens the link review list
- **THEN** candidates and evidence are shown and no confirm or reject control is rendered

### Requirement: Unavailable and empty states are explicit
When the coverage request fails, the page SHALL show that coverage is unavailable and no counts. When the period has no plays, it SHALL say there are no stored listens in the period. When a period is `insufficient_sample`, it SHALL show the usable count and the minimum.

#### Scenario: API down
- **WHEN** the coverage API is unreachable
- **THEN** the page states coverage is unavailable and renders no numbers

#### Scenario: Insufficient sample
- **WHEN** the API reports `insufficient_sample` with 12 of 20 for mood
- **THEN** the page reads "12 plays with mood analysis; 20 needed for a weekly reading"

### Requirement: The page is owner-only and accessible
Only the signed-in user's own coverage SHALL be shown; signed-out visitors SHALL get a sign-in prompt preserving the path. Counts and lists SHALL be available as keyboard-reachable tables with text labels.

#### Scenario: Signed out
- **WHEN** a signed-out visitor opens `/listening/coverage`
- **THEN** they are prompted to sign in and returned to `/listening/coverage` afterwards

### Requirement: The page plays and fetches no audio
The page SHALL contain no audio player, stream link or control that acquires audio; missing audio is listed for information only.

#### Scenario: No audio controls
- **WHEN** the page renders a list of 14 plays without a confident link
- **THEN** the rendered page contains no `audio` element and no acquisition control
