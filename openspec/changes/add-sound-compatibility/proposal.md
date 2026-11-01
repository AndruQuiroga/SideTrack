# Proposal

## Why

The vision's compatibility test compares how two people's music sounds rather than shared artists, which suits a club whose members rarely share obscure artists.

## What Changes

- Opt-in compatibility between two users from their embedded play distributions: overlap score, mood-region distance, shared themes, bridge songs and artist translation.
- Results stored with n and versions, deleted when either user leaves.

Out of scope:
- Recommendations beyond bridge songs.
- Members without opt-in or without imported history.

## Capabilities

### New Capabilities
- `analysis/sound-compatibility`: opt-in, audio-based compatibility between two users.

### Modified Capabilities
None.

## Impact

- **Observed:** a stub `compatibility` table and route exist (`sidetrack/analysis/models.py`); this change gives them real values. Depends on profiles, themes and linking. Affected: analysis, routes, web compare page.
