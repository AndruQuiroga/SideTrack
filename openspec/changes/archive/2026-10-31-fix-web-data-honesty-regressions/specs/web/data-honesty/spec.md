# Spec Delta

## MODIFIED Requirements

### Requirement: Only computed values are displayed
Scores, overlaps, recommendations, presence counts, and rating distributions SHALL be shown only when the API returned them; the site SHALL NOT substitute defaults. Live-listener and real-time-update claims SHALL require supporting data or an implemented update mechanism, respectively.

#### Scenario: Compatibility without overlap data
- **WHEN** the compatibility response has no `overlap`
- **THEN** the shared-artists and shared-genres sections say no overlap data is available

#### Scenario: Profile without a comparison
- **WHEN** a profile page is shown
- **THEN** it shows no compatibility percentage

#### Scenario: No presence evidence
- **WHEN** the API returns weeks without presence data
- **THEN** the archive and week detail show no online count or live-listener assertion, regardless of the number of weeks

#### Scenario: Missing distribution with ratings
- **WHEN** the API returns a positive rating count but no histogram
- **THEN** the page says Distribution unavailable and renders no invented histogram bins

#### Scenario: Supplied distribution
- **WHEN** the API returns histogram bins including a zero-count bin
- **THEN** the displayed bins and counts match those supplied and the zero-count bin has zero bar width

#### Scenario: No ratings
- **WHEN** the API reports zero ratings without a histogram
- **THEN** the page says No ratings yet and renders no distribution bars

#### Scenario: No update mechanism
- **WHEN** the page has no implemented real-time update mechanism
- **THEN** it makes no claim that ratings update in real time
