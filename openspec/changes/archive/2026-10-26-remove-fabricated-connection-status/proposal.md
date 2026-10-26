# Proposal

## Why

Observed: `apps/web/app/components/connections-grid.tsx` supplies a default Last.fm
connection with `linked: true`, without an API response. Settings also turns an
account-fetch failure into an empty list. These contradict `web/data-honesty`.

## What Changes

- Require real connection data instead of fabricated defaults.
- Show an explicit unavailable state when account lookup fails.
- Add rendered-component regression coverage for missing, empty and linked data.

Out of scope: provider implementations, live OAuth verification and deployment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web/data-honesty`: connection status requires account data; lookup failures are unavailable.

## Impact

Web connections component, Settings account lookup, web tests and status evidence.
