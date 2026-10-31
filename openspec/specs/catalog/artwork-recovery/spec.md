# catalog/artwork-recovery Specification

## Purpose
Recover attributable artwork for existing club music records without changing their historical meaning, and display verified covers to authorized archive readers.

## Requirements

### Requirement: Discovery preserves music identity
Recovery SHALL prefer an existing exact provider album or track identity. Without one, it SHALL accept only an unambiguous artist/title match or an explicit reviewed selection. Conflicts and uncertain edition matches SHALL remain unresolved. Discovery SHALL NOT modify records.

#### Scenario: Exact song link
- **WHEN** a stored Spotify track link resolves to matching artist/title metadata and artwork
- **THEN** preview records the exact track identity and its artwork candidate without database writes

#### Scenario: Ambiguous search
- **WHEN** artist/title search returns incompatible editions or artists without a unique defensible match
- **THEN** preview reports an unresolved record and proposes no automatic artwork update

#### Scenario: Conflicting exact identity
- **WHEN** an exact provider link resolves to a different artist or title
- **THEN** preview reports the conflict and does not substitute a search result automatically

### Requirement: Recovery uses bounded provider requests
Recovery SHALL fetch metadata and artwork validation only through supported provider endpoints and approved HTTPS image hosts. It SHALL reject arbitrary source URLs and unsafe redirects, use bounded timeouts and retries, honor rate limits, and report missing or unavailable artwork. It SHALL NOT fetch audio or unrelated Discord attachments.

#### Scenario: Unavailable provider
- **WHEN** a provider times out or rate limits beyond the retry budget
- **THEN** preview records the unavailable result and leaves the target unchanged

#### Scenario: Unsafe artwork destination
- **WHEN** an artwork candidate or redirect points to an unapproved host or a private network destination
- **THEN** validation rejects it without requesting that destination

### Requirement: Checked recovery is repeatable and preserves existing data
Apply SHALL require an exact checked plan digest and revalidate target identity and existing artwork under transaction locks. It SHALL fill missing artwork only, preserve existing covers, and record provider identity and recovery evidence. A stale plan SHALL fail atomically. An identical retry SHALL create no duplicates or additional changes.

#### Scenario: Concurrent cover change
- **WHEN** a target receives a cover after its recovery plan was checked
- **THEN** applying that stale plan fails without any partial updates

#### Scenario: Identical retry
- **WHEN** the same successful checked recovery is applied again
- **THEN** the same covers and evidence remain with no duplicate rows

### Requirement: Artwork does not reinterpret imported history
Recovery SHALL preserve music titles, artists, dates, winners, nominations, ratings, attribution, accounts, links and access. It SHALL create no notifications, schedules or audio jobs. Existing history verification and erasure-aware replay SHALL continue to work without rewriting the original source evidence or approved digest.

#### Scenario: Recovery after history import
- **WHEN** verified artwork is applied to imported albums and songs
- **THEN** history verification succeeds, repeated import adds no records, protected history fields remain equal and delivery/job counts are unchanged

### Requirement: Authorized archive readers see verified artwork
Album and Singles Night views SHALL display stored artwork with descriptive alternative text and an explicit unavailable state for missing or failed images. Singles Night API artwork SHALL be optional and retain existing access rules. Browser bundles SHALL contain no provider or API credentials, private plans or export contents.

#### Scenario: Singles artwork and missing image
- **WHEN** a member opens a session containing one song with verified artwork and one without it
- **THEN** the first song displays its cover and the second displays Artwork unavailable, with ratings unchanged

#### Scenario: Rejected image load
- **WHEN** a stored cover fails to load
- **THEN** the view displays Artwork unavailable without replacing it with unrelated imagery

#### Scenario: Unauthorized session request
- **WHEN** an anonymous visitor or signed-in non-member requests Singles Night details
- **THEN** existing sign-in or access-denied behavior remains and no private session data is disclosed
