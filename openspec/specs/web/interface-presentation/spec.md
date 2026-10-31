# web/interface-presentation Specification

## Purpose
Defines a restrained, readable presentation and consistent interaction states across SideTrack's web application.

## Requirements

### Requirement: Content carries the visual hierarchy
Pages SHALL use solid neutral application surfaces, consistent typography, and visibly distinct navigation, actions, and metadata. The shell and shared controls SHALL NOT use decorative glow fields, multicolor gradient chrome, emoji feature tiles, or status dots without a stated status. Album artwork SHALL remain visually distinct from its surrounding controls.

#### Scenario: Shared visual language
- **WHEN** Overview, Club, Listening, Account, and sign-in render
- **THEN** they share navigation and control treatments without decorative gradient panels or unlabeled activity dots

### Requirement: Access and data states have distinct messages
Pages SHALL distinguish signed-out, forbidden, empty, no matches, unavailable, and not-found outcomes. Failed optional requests SHALL NOT be represented as successful empty collections. A retry action SHALL appear only where it performs a request or reload; it SHALL NOT claim success before completion.

#### Scenario: Connection lookup fails
- **WHEN** the linked-account request fails
- **THEN** Account says Connections unavailable and renders no disconnected or connected account claims

#### Scenario: Empty account list
- **WHEN** the linked-account request succeeds with no Last.fm account
- **THEN** Account offers the supported Last.fm connection action without claiming an outage

### Requirement: Connection descriptions match supported capabilities
Account and sign-in screens SHALL describe Discord as identity and Last.fm as the supported listening-import connection. Spotify SHALL be described as metadata-only without personal linking, now-playing, audio-feature, or recommendation promises. Existing legacy Spotify account records SHALL NOT enable a new Spotify connect action.

#### Scenario: Connection choices
- **WHEN** Account renders a successful linked-account lookup
- **THEN** it offers supported Last.fm connection controls and shows Discord identity
- **AND** it contains no Connect Spotify or unsupported import-progress claim

### Requirement: Keyboard and touch users can complete navigation
Interactive controls SHALL have accessible names, visible focus, and sufficient target size or spacing to meet WCAG 2.2 AA. Search SHALL be dismissible with Escape, contain keyboard focus while open, and restore focus when closed. Search results SHALL distinguish available destinations from noninteractive metadata.

#### Scenario: Search keyboard journey
- **WHEN** a keyboard user opens Search, navigates its controls, and presses Escape
- **THEN** focus never escapes into obscured content while the dialog is open and returns to the invoking control when closed

#### Scenario: Record without a destination
- **WHEN** a search result has metadata but no supported internal detail route or supplied external URL
- **THEN** it appears as readable metadata without a clickable control that leads nowhere

### Requirement: Layout and text remain readable
Pages SHALL reflow at 320 CSS pixels without horizontal page scrolling, except genuinely two-dimensional tables with contained scrolling. Text SHALL meet WCAG AA contrast, dates SHALL identify the displayed timezone, and reduced-motion preferences SHALL suppress nonessential motion. Status meaning SHALL be conveyed with text as well as any color.

#### Scenario: Narrow week page
- **WHEN** a week detail is viewed at 320 CSS pixels
- **THEN** its album identity, schedule, Discord link, and ratings remain readable and operable without horizontal page scrolling

#### Scenario: Reduced motion
- **WHEN** reduced motion is enabled
- **THEN** navigation and state changes remain understandable without decorative animation
