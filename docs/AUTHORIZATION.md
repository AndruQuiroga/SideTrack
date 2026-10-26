# API authorization

ADR 0009 is implemented in `sidetrack/identity/auth.py` (change
`add-per-user-authorization`). This page is the route policy table;
`services/api/tests/test_route_policies.py` fails when it disagrees with the
registered routes.

## Callers

| Client | Token | Acts for | Scopes acting as itself | Scopes acting for a user |
| --- | --- | --- | --- | --- |
| `web` | `SIDETRACK_WEB_API_TOKEN` | `X-Sidetrack-Act-As: user:<uuid>` from its server session | `identity:provision` | `catalog:*`, `club:read`, `club:write`, `identity:self`, `personal:read`, `personal:write` |
| `bot` | `SIDETRACK_BOT_API_TOKEN` | `X-Sidetrack-Act-As: discord:<snowflake>`, resolved through the linked Discord account | `identity:provision`, `club:membership`, `club:read`, `club:threads`, `club:notifications`, `catalog:read` | `catalog:*`, `club:read`, `club:write` |

`analysis:write` is held by no client: the GPU worker calls analysis code directly
(ADR 0001). The shared `SIDETRACK_API_TOKEN` is retired and grants nothing.

Failures: 401 `unauthorized` (no or unknown token), 400 `bad_actor` (malformed
header), 403 `forbidden`, `unknown_actor`, `actor_required` or
`not_a_club_member`, and 404 for personal resources the caller may not see.
Request logs record `client=` and `actor=` with the request ID, never tokens.

## Data rules

- **Club data** (weeks, nominations, ratings, summaries, trending, feed, member
  lists): current club members, or the bot acting as itself.
- **Ballots**: only the voter, through an acting user. No client reads ballots as
  itself.
- **Admin**: creating weeks, changing week fields other than thread IDs,
  overriding winners, deleting ratings and editing albums need an acting user with
  role `admin`. The bot acting as itself may set only week thread IDs.
- **Membership**: written only by the bot acting as itself and by
  `python -m sidetrack.club_admin grant-admin` (the operator's database access).
- **Personal data**: listen events, recent listening and taste profiles are visible
  to the owner, and to club members when the owner set `listening_visibility` to
  `club`. Linked accounts and recommendations are owner-only. Compatibility needs
  both users to be members, and the other user to share with the club. Job status
  is visible only to the user who submitted the job.
- **Provisioning**: the web and bot clients acting as themselves create users,
  look users up by provider ID, and attach a first Discord account to a user who
  has none.
- **Writes** take the owner from the acting user. A body or query `user_id` that
  differs is refused with 403.

## Route policies

| Method | Path | Policy | Rule |
| --- | --- | --- | --- |
| GET | `/health` | public | |
| POST | `/integrations/lastfm/callback` | public | Authorized by its signed `state` |
| DELETE | `/admin/ratings/{rating_id}` | `club:write` | Admin |
| POST | `/admin/weeks/{week_id}/override-winner` | `club:write` | Admin |
| POST | `/albums/` | `catalog:write` | Member |
| POST | `/albums/resolve` | `catalog:write` | Member |
| GET | `/albums/search` | `catalog:read` | Any caller with the scope |
| GET | `/albums/{album_id}` | `catalog:read` | Any caller with the scope |
| PATCH | `/albums/{album_id}` | `catalog:write` | Admin |
| POST | `/albums/{album_id}/enrich` | `catalog:write` | Member |
| DELETE | `/club/members/discord/{discord_id}` | `club:membership` | Bot as itself |
| PUT | `/club/members/discord/{discord_id}` | `club:membership` | Bot as itself |
| POST | `/club/notifications/claim` | `club:notifications` | Bot as itself |
| POST | `/club/notifications/{event_id}/ack` | `club:notifications` | Bot as itself |
| POST | `/club/notifications/{event_id}/fail` | `club:notifications` | Bot as itself |
| GET | `/feed` | `club:read` | Member; `user_id` must be the actor |
| POST | `/ingest/lastfm` | `personal:write` | Owner |
| POST | `/integrations/{provider}/connect` | `identity:self` | Owner |
| GET | `/jobs/{job_id}/status` | `personal:read` | Submitter |
| GET | `/listen-events/` | `personal:read` | Owner, or member if shared; defaults to the actor |
| POST | `/listen-events/` | `personal:write` | Owner |
| GET | `/listen-events/{listen_event_id}` | `personal:read` | Owner, or member if shared |
| GET | `/nominations/` | `club:read` | Member |
| DELETE | `/nominations/{nomination_id}` | `club:write` | Nominator or admin |
| GET | `/nominations/{nomination_id}` | `club:read` | Member |
| PATCH | `/nominations/{nomination_id}` | `club:write` | Nominator or admin |
| GET | `/ratings` | `club:read` | Member |
| GET | `/ratings/{rating_id}` | `club:read` | Member |
| GET | `/recommendations` | `personal:read` | Owner |
| GET | `/search` | `catalog:read` | People only for members, and only members are found |
| GET | `/tracks/pending-features` | `analysis:write` | No client |
| POST | `/tracks/{track_id}/features` | `analysis:write` | No client |
| GET | `/trending` | `club:read` | Member |
| GET | `/users/` | `club:read` | Member; lists current members |
| POST | `/users/` | `identity:provision` | Client as itself |
| GET | `/users/lookup/by-provider/{provider}/{provider_user_id}` | `identity:provision` | Client as itself |
| GET | `/users/{user_a}/compatibility/{user_b}` | `personal:read` | One of the pair, both members, the other shares |
| DELETE | `/users/{user_id}` | `identity:self` | Owner |
| GET | `/users/{user_id}` | `club:read \| identity:self` | Owner, or member viewing a member |
| PATCH | `/users/{user_id}` | `identity:self` | Owner |
| DELETE | `/users/{user_id}/follow/{target_id}` | `identity:self` | Owner as follower |
| POST | `/users/{user_id}/follow/{target_id}` | `identity:self` | Owner as follower |
| GET | `/users/{user_id}/followers` | `club:read` | Member |
| GET | `/users/{user_id}/following` | `club:read` | Member |
| GET | `/users/{user_id}/linked-accounts` | `identity:self` | Owner |
| POST | `/users/{user_id}/linked-accounts` | `identity:provision \| identity:self` | Owner, or provisioning a first Discord account |
| DELETE | `/users/{user_id}/linked-accounts/{provider}/{provider_user_id}` | `identity:self` | Owner |
| GET | `/users/{user_id}/listening/recent` | `personal:read` | Owner, or member if shared |
| GET | `/users/{user_id}/taste-profiles/` | `personal:read` | Owner, or member if shared |
| POST | `/users/{user_id}/taste-profiles/recompute` | `personal:write` | Owner |
| GET | `/votes` | `club:write` | The actor's own votes |
| GET | `/votes/{vote_id}` | `club:write` | The voter only |
| GET | `/weeks/` | `club:read` | Member |
| POST | `/weeks/` | `club:write` | Admin |
| GET | `/weeks/{week_id}` | `club:read` | Member |
| PATCH | `/weeks/{week_id}` | `club:threads \| club:write` | Admin; bot as itself sets thread IDs only |
| POST | `/weeks/{week_id}/nominations` | `club:write` | Member, as themselves |
| POST | `/weeks/{week_id}/ratings` | `club:write` | Member, as themselves |
| GET | `/weeks/{week_id}/ratings/summary` | `club:read` | Member |
| POST | `/weeks/{week_id}/votes` | `club:write` | Member, as themselves |
