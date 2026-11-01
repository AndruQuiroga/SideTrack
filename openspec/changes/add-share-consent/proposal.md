# Proposal

## Why

Listeners want to share a listening card. The research notes (section 4) and mockup 13
put conditions on that:

- Nothing is shared until the person explicitly asks.
- Another member's data needs that member's separate consent.
- Private check-ins are excluded by default.
- The destination, what can be revoked and the limits of retracting an exported image are
  all explained.
- Every card carries its units and its ranking source.
- Nothing on a card makes a personality claim.

Today Sidetrack has no sharing path at all. Personal listening is either `private` or
visible to the club. If sharing were added casually, it would become a silent new
visibility tier.

## What Changes

- **An explicit share preview.** The owner picks items from an allow-list: top tracks and
  period, sample size and analysis coverage, listening clock, theme estimates, mood estimates and check-in. The
  API renders exactly what would leave the account as a frozen snapshot, and that
  snapshot is what the owner previews.
- **Opt-in share links created only from a previewed snapshot.** Each link uses an
  unguessable token stored hashed, has an expiry (default 30 days, maximum 365), and can
  be revoked at any time.
  - A revoked or expired link returns 410 with no data.
  - Revoking a link deletes its snapshot.
  - Deleting the account revokes all of its links.
- **Check-ins are excluded by default.** A check-in item needs a second explicit
  confirmation in the preview. Check-ins are otherwise visible only to their owner.
- **Another member's data is never included in v1.** Compatibility and blend outputs
  cannot be shared. Their consent model (`add-sound-compatibility`) does not extend to
  public sharing.
- **Each card states its basis.** Every card states:
  - the period and timezone;
  - units such as plays or included plays;
  - the ranking source, for example "ranked by your included plays from ListenBrainz";
  - the sample size and analysis coverage;
  - for gated estimates, their gate status.

  Theme or mood items are offered only when their evaluation gate is `approved`. Mood
  values are shown as raw scores or the owner's own percentiles, never cross-user
  comparisons.
- **No personality, feeling or diagnosis claims.** A guard test rejects them in card text.
- **The display name is off by default.** Sharing does not change `listening_visibility`.
- **A destination and retraction explanation**:
  - who can open the link: anyone holding it;
  - that the page is not indexed by search engines;
  - that revoking stops the link but cannot retract screenshots or images already
    downloaded.

Out of scope:
- Audio, previews, stream URLs, file paths and cover-art files. Cards carry metadata only.
- Posting to third-party platforms. The owner copies the link. There are no OAuth posting
  integrations.
- Discord sharing. The weekly club card stays DM-only (`add-listening-visuals`), and this
  change does not post to channels.
- Shares that include another member's data. This would need a two-party consent design
  and becomes a follow-up change.
- Analytics on who opened a link. Only an open count is stored, and no viewer identity.

## Capabilities

### New Capabilities
- `identity/share-consent`: the shareable-item allow-list, frozen snapshots, opt-in
  links, expiry, revocation, deletion cascade, the check-in and other-member exclusions,
  and the card content rules.
- `web/share-preview`: the owner's share builder and preview, link management, and the
  public read-only card page.

### Modified Capabilities
- `identity/personal-data-visibility`: adds the requirement that a revocable share
  snapshot is the only way personal listening data reaches anyone outside the owner's
  visibility, and that sharing never changes `listening_visibility`.

## Impact

Depends on:
- `add-weekly-listening-profile`:
  - `analysis/weekly-listening-profile` supplies the period figures, included plays and
    coverage.
  - `analysis/mood-check-ins` supplies the check-ins, which are owner-only.
- `add-listening-visuals`: the listening-clock item. It is offered only once that change
  lands, and is otherwise `item_unavailable`.
- `add-music-analysis-evaluation-protocol`: gate status for theme and mood items.
- Optional: `add-sound-themes` and `add-track-mood-scores` for the theme and mood items.

Current state:
- **Observed:** `User.listening_visibility` is `private` or `club`, defaulting to
  `private` (`sidetrack/identity/models.py`; `openspec/specs/identity/personal-data-visibility`).
- **Observed:** other callers get 404 for private listening data
  (`openspec/specs/identity/personal-data-visibility`).
- **Observed:** account deletion cascades to a user's data
  (`openspec/specs/identity/account-deletion`).
- **Observed:** no share, token or public-card route or table exists. This was checked
  by searching `sidetrack/` and `apps/web/app/` for share routes.
- **Assumed:** the web app is publicly reachable through the existing Cloudflare Tunnel
  deployment (ADR 0006, `deploy/`), so a link opens without signing in.

Affected:
- `sidetrack/identity/` (share tables and routes; the identity domain owns consent);
- `migrations/`;
- `apps/web/app/share/` and `apps/web/app/settings/` (link management);
- `packages/api-client`;
- `docs/AUTHORIZATION.md` (the share rules);
- `docs/status.yaml`.
