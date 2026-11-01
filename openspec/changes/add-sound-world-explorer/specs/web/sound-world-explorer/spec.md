# Spec Delta

## Purpose

Lets a listener browse their own candidate sound-worlds as an accessible list, see the tracks and plays behind each, compare weeks, and find real nearest neighbours, while labels stay visibly suggestions and missing data stays visible.

## ADDED Requirements

### Requirement: The explorer is owner-only and shows only API data
The `/listening/sound-worlds` page SHALL show only the signed-in user's own themes as returned by the API. Requests for another user's themes SHALL respond 404. When the API fails, the page SHALL show an unavailable state and no themes.

#### Scenario: API down
- **WHEN** the API is unreachable and the user opens the explorer
- **THEN** the page says sound-worlds are unavailable and lists no themes

#### Scenario: Another member's themes
- **WHEN** user U requests user V's themes through the API
- **THEN** the API responds 404

### Requirement: Themes are listed with denominators and suggestion labels
Each theme SHALL show the user's display name if set, otherwise its suggested terms marked as suggestions, plus its representative tracks and its track count out of the user's eligible tracks. A theme with no confident term SHALL be shown as unnamed, not given an invented name.

#### Scenario: Library view
- **WHEN** a user has 3 themes over 400 eligible tracks
- **THEN** each theme row shows its track count out of 400, up to three representative tracks, and either the user's name or terms marked "suggested"

#### Scenario: Abstained label
- **WHEN** a theme has no term that met the abstention threshold
- **THEN** its row says no confident label and shows its representative tracks

### Requirement: Unassigned tracks and plays stay visible
The page SHALL show the number of eligible tracks, and in week view included plays, that belong to no theme as "Other or uncertain", and the theme counts plus that count SHALL equal the stated denominator.

#### Scenario: Week view totals
- **WHEN** a week has 61 included plays with usable audio, 38 in themes and 23 unassigned
- **THEN** the page shows 61 as the denominator, the theme play counts summing to 38, and 23 as other or uncertain

### Requirement: Week view uses stored weekly shares
In week view each theme SHALL show play count and share of the week's included plays with usable audio, as stored by the weekly profile. A week the profile reports `not_enough_listening` or has no profile for SHALL show that state and no shares.

#### Scenario: Insufficient week
- **WHEN** the selected week's profile is `not_enough_listening`
- **THEN** the page states there was not enough listening with analysed audio that week and shows no percentages

### Requirement: Two weeks can be compared with separate denominators
The user SHALL be able to compare two weeks side by side; each column SHALL show its own denominator, and a theme absent in one week SHALL show zero plays only when that week has a profile, otherwise the column shows the insufficient state.

#### Scenario: Comparing weeks
- **WHEN** the user compares a week with 61 included plays and one with 40
- **THEN** each column shows its own denominator and shares computed against it

### Requirement: Neighbours come from the original vector space
Theme detail SHALL list member tracks, and selecting a track SHALL list its nearest neighbours within the user's eligible library ranked by cosine in the original embedding space of the current model revision, never by map position.

#### Scenario: Neighbours of a member
- **WHEN** the user selects a track in a theme
- **THEN** up to 10 neighbours are listed, all from the user's eligible library, in descending cosine order, excluding the track's own other assets

#### Scenario: Track without current embedding
- **WHEN** the selected track has no current embedding
- **THEN** the page says it has not been analysed with the current model and lists no neighbours

### Requirement: The map is optional and labelled as a projection
The explorer SHALL work fully as a list. Where a stored projection exists, a link SHALL open the map filtered to a theme, showing that distances and clusters on the map are distorted; where none exists, no map link SHALL be shown.

#### Scenario: No projection
- **WHEN** the user has no stored projection for the current revision
- **THEN** the explorer shows no map link and every function remains available in the list

### Requirement: Missing, stale and small libraries are explicit
The page SHALL show distinct messages for no themes built, `not_enough_tracks`, and `stale` (themes built from an older embedding revision or vocabulary than current); stale themes SHALL be shown only with that notice.

#### Scenario: Not enough tracks
- **WHEN** the API reports `not_enough_tracks`
- **THEN** the page says the library has too few analysed tracks to form sound-worlds and lists none

#### Scenario: Stale build
- **WHEN** the themes were built with an older embedding revision
- **THEN** each theme is shown under a notice that the sound-worlds are out of date

### Requirement: Label method is disclosed
The page SHALL offer a "label method" panel naming the model and revision, vocabulary version, ranking method version and clustering version, and stating that labels are model suggestions about at most the first three minutes of each track, not genre facts or statements about the listener.

#### Scenario: Opening the method panel
- **WHEN** the user opens the label method panel
- **THEN** it shows the versions returned by the API and the suggestion and three-minute notes

### Requirement: The explorer is accessible without color or a pointer
Themes SHALL be distinguished by text and pattern or shape as well as color, every control SHALL be keyboard-operable with visible focus, updates SHALL be announced to screen readers, and animation SHALL be disabled when the user prefers reduced motion.

#### Scenario: Grayscale distinction
- **WHEN** the explorer is rendered with colors removed
- **THEN** every theme remains identifiable by its text label and pattern

#### Scenario: Reduced motion
- **WHEN** the browser reports prefers-reduced-motion
- **THEN** no transition or animation runs when switching weeks or themes

### Requirement: The explorer is metadata-only
The page SHALL NOT play audio or link to audio files or streams.

#### Scenario: No audio elements
- **WHEN** any explorer view is rendered
- **THEN** it contains no audio or video element and no link to an audio file path or stream URL
