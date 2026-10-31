# web/data-honesty Specification

## Purpose
Guarantees that everything the Sidetrack website shows came from the API, and that missing data or an unavailable API is shown as such rather than replaced with invented content.

## Requirements

### Requirement: No invented data on API failure
When an API request a page depends on fails, the page SHALL show an "unavailable" state and SHALL NOT render sample, demo or generated substitute data.

#### Scenario: Club archive with the API down
- **WHEN** the API is unreachable and a visitor opens `/club`
- **THEN** the page states that the club archive is unavailable
- **AND** no week, album, rating or nomination is listed

#### Scenario: Profile with the API down
- **WHEN** the API is unreachable and a visitor opens `/u/<id>`
- **THEN** the page states that the profile is unavailable and shows no artists, genres, metrics or timeline

#### Scenario: Blend request fails
- **WHEN** generating a blend fails
- **THEN** the page shows an error and no track list

### Requirement: Missing records are not found
A page for a specific record SHALL respond with the not-found page when the API reports that the record doesn't exist.

#### Scenario: Unknown week
- **WHEN** a visitor opens `/club/weeks/<id>` for a week the API answers 404 for
- **THEN** the site responds with its not-found page

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

### Requirement: No links to fictional users
Navigation and pages SHALL NOT link to placeholder users such as `demo`.

#### Scenario: Navigation
- **WHEN** any page renders the navbar or command palette
- **THEN** no link targets a `demo` user or a comparison of placeholder users

### Requirement: Regressions are caught automatically
The web test suite SHALL fail if source under `apps/web/app` reintroduces fallback generators, demo users or random data.

#### Scenario: Guard test
- **WHEN** a source file under `apps/web/app` contains `Math.random`, `WithFallback`, `source: 'fallback'` or a `demo` user reference
- **THEN** `pnpm --filter @sidetrack/web test` fails and names the file

### Requirement: Account connection status comes from account data
Connection controls SHALL display linked status only from supplied account data.
When account lookup fails, Settings SHALL display an unavailable state rather
than treating the failure as an empty list or a connected account.

#### Scenario: Account lookup unavailable
- **WHEN** the linked-account API fails
- **THEN** Settings states that linked accounts are unavailable and shows no linked status

#### Scenario: No linked accounts
- **WHEN** the API returns an empty account list
- **THEN** Settings shows the supported connection controls as not linked

#### Scenario: A linked Last.fm account
- **WHEN** the API returns a linked Last.fm account
- **THEN** Settings displays that account as linked
