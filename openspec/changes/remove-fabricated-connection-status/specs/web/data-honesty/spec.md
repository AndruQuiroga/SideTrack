## ADDED Requirements

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
