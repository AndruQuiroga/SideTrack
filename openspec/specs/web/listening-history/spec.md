# web/listening-history Specification

## Purpose
Provides a usable personal listening log from supported recent-listen records without requiring profile analytics or overstating import coverage.

## Requirements

### Requirement: Personal history has a direct entry
`/listening` SHALL resolve the signed-in user's history from the server session without calling a profile endpoint. Signed-out visitors SHALL receive a sign-in prompt that preserves `/listening`. Existing `/u/<id>/listening` access SHALL continue to follow the owner's visibility policy.

#### Scenario: Owner opens Listening
- **WHEN** signed-in user U activates Listening
- **THEN** the site fetches U's recent listens acting as U and renders history without requesting profile analytics

#### Scenario: Another private history
- **WHEN** U opens V's history and V has not shared it
- **THEN** the page renders no listening records and explains that the history is unavailable to this viewer without exposing V's account details

### Requirement: History preserves pagination and temporal context
History SHALL display track, artist, timestamp, and supplied source in consistent rows. Day grouping and timestamps SHALL use UTC with a visible UTC label. Pagination SHALL preserve the selected user and the existing 50-record page size, and malformed page parameters SHALL use page zero.

#### Scenario: Crossing a UTC day
- **WHEN** two records occur at 23:59 UTC and 00:01 UTC on successive dates
- **THEN** they appear under the corresponding separate UTC date headings and retain correct displayed times

#### Scenario: Older page
- **WHEN** a 50-record history page is loaded and the user activates Older
- **THEN** the next page requests the next 50 records for the same user and provides a Newer link

### Requirement: Coverage language describes stored records
History SHALL be described as available or stored listening history, not a complete or full history. Empty history SHALL explain the supported Last.fm connection path without promising backfill, live presence, or Spotify tracking. Request failures SHALL show an unavailable state instead of an empty log.

#### Scenario: No imported records
- **WHEN** the recent-listen API successfully returns no records
- **THEN** the page says No stored listens and offers Account as the supported connection destination

#### Scenario: Import coverage unknown
- **WHEN** records exist but the API provides no import-coverage or synchronization metadata
- **THEN** the page shows the records without claiming complete history, a last-sync time, or import progress
