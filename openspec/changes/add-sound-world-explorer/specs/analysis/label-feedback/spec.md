# Spec Delta

## Purpose

Stores a listener's own verdicts on generated theme terms and track tags so their display reflects their corrections, while keeping those verdicts private, exportable, deletable and isolated from other users and from model training.

## ADDED Requirements

### Requirement: Users can accept or reject a suggested label
A user SHALL be able to record `accepted` or `rejected` for a suggested term on one of their own themes, or for a suggested tag on an asset in their eligible library. Recording a verdict again for the same target SHALL replace the earlier one. Verdicts on another user's themes SHALL respond 404.

#### Scenario: Rejecting a theme term
- **WHEN** a user rejects the term "ambient" on their theme T
- **THEN** a verdict `rejected` is stored for (T, "ambient") and the API returns it

#### Scenario: Changing a verdict
- **WHEN** the user later accepts the same term on T
- **THEN** only one verdict exists for (T, "ambient") and it is `accepted`

#### Scenario: Another user's theme
- **WHEN** user U posts a verdict on user V's theme
- **THEN** the API responds 404 and stores nothing

### Requirement: Rejected labels stop being suggested to that user only
A term the user rejected SHALL no longer be shown as a suggestion on that theme or asset for that user, and SHALL remain listed as rejected with an undo. Other users' suggestions and stored model outputs SHALL be unchanged.

#### Scenario: Hidden for owner, unchanged for others
- **WHEN** user U rejects tag "jazz" on asset A and user V also has A in their library
- **THEN** U's view of A no longer suggests "jazz" but lists it as rejected, and V's view of A still suggests "jazz"

#### Scenario: Undo
- **WHEN** U deletes the rejection
- **THEN** "jazz" is suggested to U again on A if the model still ranks it above the threshold

### Requirement: Renaming uses the theme display name
Renaming a theme from the explorer SHALL set the theme's user display name as defined by `analysis/sound-themes` and SHALL be listed with the user's label feedback.

#### Scenario: Rename appears in feedback list
- **WHEN** a user renames theme T to "Late static"
- **THEN** T's display name is "Late static" and the user's feedback list includes the rename

### Requirement: Verdicts survive rebuilds only with sufficient overlap
When themes are rebuilt, a theme-term verdict SHALL move to the new theme only when the sound-themes carry-over rule matches it; otherwise it SHALL be reported `orphaned` with its old term and listed for review. Asset-tag verdicts SHALL be keyed by asset and vocabulary term and SHALL be reported `orphaned` when the term leaves the vocabulary.

#### Scenario: Low-overlap rebuild
- **WHEN** a rebuild produces no theme meeting the carry-over rule for theme T
- **THEN** T's verdicts are listed as `orphaned` and are not applied to any new theme

#### Scenario: Term removed from vocabulary
- **WHEN** the vocabulary version drops the term "lo-fi"
- **THEN** the user's verdict on "lo-fi" for asset A is listed as `orphaned`

### Requirement: Feedback is private personal data
Label feedback SHALL be readable only by its owner regardless of `listening_visibility`, and SHALL never appear in club views, weekly cards or another user's pages.

#### Scenario: Club visibility does not expose feedback
- **WHEN** user U has `listening_visibility` set to club and member V requests U's label feedback
- **THEN** the API responds 404

### Requirement: Feedback is exportable
The owner SHALL be able to export all their label feedback and theme renames as JSON, each entry with target, term, verdict or name, timestamps and status (`active` or `orphaned`).

#### Scenario: Export contents
- **WHEN** a user with 3 verdicts and 1 rename requests the export
- **THEN** the JSON contains exactly those 4 entries with their fields

### Requirement: Feedback is deletable
The owner SHALL be able to delete one verdict or all their label feedback; deleting all SHALL also clear their theme renames. Account deletion SHALL remove all label feedback.

#### Scenario: Delete all
- **WHEN** a user deletes all their label feedback
- **THEN** their verdict list and export are empty and their themes show suggested terms again

#### Scenario: Account deletion
- **WHEN** the user's account is deleted
- **THEN** no label-feedback row references that user

### Requirement: Feedback never changes models or evaluation
Label feedback SHALL NOT retrain, recalibrate or alter any model, vocabulary, threshold or stored model output, and SHALL NOT be read by evaluation tooling.

#### Scenario: Stored outputs unchanged
- **WHEN** a user rejects a tag on an asset
- **THEN** the stored model tag scores for that asset are identical before and after
