# Spec Delta

## Purpose

Provides predictable navigation to supported SideTrack tasks while preserving existing links and authenticated destinations.

## ADDED Requirements

### Requirement: Primary navigation names usable destinations
The website SHALL provide Overview, Club, Listening, Search, and Account entry points with a visible current location. Unsupported discovery, feed, profile, compatibility, and blend features SHALL NOT be promoted in primary navigation or overview actions.

#### Scenario: Member navigation
- **WHEN** a signed-in member opens the overview
- **THEN** primary navigation exposes those five entry points and marks Overview as current
- **AND** no primary action promotes recommendations, compatibility, blends, or an unavailable profile

#### Scenario: Search entry
- **WHEN** a user activates Search by keyboard or pointer
- **THEN** an accessible search dialog opens with a named field and close control
- **AND** closing it returns focus to its invoking control

### Requirement: Navigation remains usable on narrow screens
Primary destinations SHALL be reachable with visible labels on mobile. Opening mobile navigation SHALL expose its expanded state, and selecting a destination SHALL close it and update the current-location indicator.

#### Scenario: Mobile navigation
- **WHEN** a user opens navigation at 320 CSS pixels and selects Club
- **THEN** the Club entry opens without horizontal page scrolling and the menu closes

### Requirement: Overview is useful without unsupported claims
The overview SHALL show an accurate sign-in introduction to visitors. For signed-in users it SHALL independently load accessible club context and their recent listens, distinguishing empty, denied, and unavailable sections. It SHALL NOT require a profile or recommendation endpoint to render.

#### Scenario: Signed-out overview
- **WHEN** a visitor opens `/`
- **THEN** a concise Discord sign-in action is shown without club or listening records and without credentialed API requests

#### Scenario: Independent section failure
- **WHEN** the user's recent listens load but their club request is denied or unavailable
- **THEN** the recent listens remain visible and the club section explains its own state

### Requirement: Existing routes remain understandable
`/club`, `/club/weeks/<id>`, `/settings`, `/login`, and `/u/<id>/listening` SHALL retain their supported purposes. Unsupported feature URLs SHALL retain the shared shell and show a specific limitation with a link to Overview or Club, without invoking known absent feature endpoints. Unknown week records SHALL retain not-found behavior.

#### Scenario: Legacy blend URL
- **WHEN** a user directly opens `/blend`
- **THEN** the page states that blend generation is unavailable and offers a usable onward destination without attempting generation

#### Scenario: Existing archive link
- **WHEN** a member opens an existing `/club/weeks/<id>` link for a stored week
- **THEN** the corresponding week remains reachable

### Requirement: Sign-in preserves a safe return destination
Sign-in links from protected pages SHALL preserve the same-origin relative destination and its supported view-state parameters. External or malformed destinations SHALL fall back to Overview.

#### Scenario: Return to filtered archive
- **WHEN** a visitor signs in from `/club?q=ambient&sort=rating&view=list`
- **THEN** successful sign-in returns them to that archive view

#### Scenario: External return URL
- **WHEN** the sign-in return parameter names an external origin
- **THEN** successful sign-in returns to `/` rather than redirecting externally
