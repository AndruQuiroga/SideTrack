# Design

## Context

See proposal.md. Sources:
- Mockup 13 and the anti-patterns in `docs/research/MOCKUPS.md`.
- Notes section 4:
  - user jobs;
  - "each participant controls access and deletion";
  - units and ranking source;
  - no personality claims.
- Notes section 3, step 5: owner gate before user-facing claims.

Constraints:
- Personal data is private by default (`identity/personal-data-visibility`).
- Deletion cascades (`identity/account-deletion`).
- Postgres is the only stateful service.
- No audio is served over HTTP.
- No secrets in logs.
- The weekly club card is sent by DM only.
- Check-ins are visible only to their owner.
- Compatibility has no single percentage. `not_opted_in` must not reveal which side
  declined.

## Goals / Non-Goals

**Goals:**
- A share contains exactly what the owner previewed.
- Every share can be revoked, and expires by default.
- Sharing never changes visibility.

**Non-Goals:**
- Two-party shares.
- Platform posting.
- Image export generation.
- Viewer analytics.

## Decisions

### D1. Frozen snapshots, not live queries
The preview stores a JSON snapshot in `share_snapshots`, with the owner, the items, the
period, the item versions and the created timestamp. The public page reads only this
row.

Alternative rejected: render live data through a token. The page could drift from what
the owner previewed, and it would widen the read path into private tables.

### D2. Tokens
Each link token has 32 random bytes from `secrets.token_urlsafe`. Only its SHA-256 hash
is stored in `share_links`, which also holds the expiry, `revoked_at` and the open count.
Lookup is by hash. Tokens never appear in logs, and the request-logging middleware
redacts `/share/` paths.

Alternative rejected: signed stateless tokens. They cannot be revoked without a
denylist.

### D3. Revocation deletes the snapshot
On revoke, the link row is kept with `revoked_at` so that the link returns 410. The
snapshot row is deleted, which minimises retained data.

Expiry is enforced at read time. A daily cleanup job on the Postgres queue deletes
expired snapshots.

### D4. Item allow-list and composition
Each item has a builder in the domain that owns its data:
- top tracks and sample: listening;
- clock: visuals;
- theme and mood: analysis.

Each builder is called through its public read model and returns fixed fields only. The
identity domain owns consent, links and snapshots, and calls the builders through
`sidetrack` public operations, following `docs/MODULES.md`.

Unimplemented items report `item_unavailable`. Theme and mood items check the evaluation
register gate.

### D5. Check-in double opt-in
The check-in item needs both selection and `confirm_check_in: true` on publish. The UI
shows a separate dialog. This is deliberately redundant in the API, so that a client bug
cannot leak check-ins.

### D6. No other-member data
Any item sourced from compatibility, blend or compare is rejected with 422. Two-party
consent and revocation would need their own design (`add-sound-compatibility` handles
consent for the club, not the public). Rejecting these items also avoids revealing
whether another member opted in.

### D7. Claim guard
The snapshot schema has no free-text fields. A test runs every item combination against
a list of prohibited terms covering personality, feelings, diagnoses and percentage
compatibility.

### D8. Web
- `/listening/share`: the builder.
- `/settings`: a "Shared links" section.
- `/share/[token]`: the public, unauthenticated card. It sends `X-Robots-Tag: noindex`
  and a robots meta tag, has no audio elements, and does not hotlink artwork.

## Risks / Trade-offs

- **Screenshots cannot be retracted.** The builder explains this explicitly before
  publishing.
- **Links forwarded beyond the intended audience.** Links expire by default, can be
  revoked, show no identity by default, and record no viewer identity.
- **Public exposure through the tunnel.** Only `/share/[token]` is unauthenticated. The
  token is unguessable, and requests are rate-limited at the app with the existing
  middleware where available.
- **Item builders land in other changes.** Those items stay `item_unavailable` until
  they land.

## Migration Plan

An additive migration creates `share_snapshots` and `share_links`, with ON DELETE
CASCADE from users. To roll back, drop both tables and remove the routes. All links then
fail closed with 404.

## Open Questions

- Should cover artwork be allowed on cards if it is hosted from the club's own artwork
  store (`docs/ARTWORK.md`)? It is excluded in v1.
- Is a downloadable image export wanted at all, given that it cannot be retracted?
- Should the open count be shown to the owner, or not stored at all?
