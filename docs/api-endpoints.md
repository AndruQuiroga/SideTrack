# API Endpoint Inventory

This document maps core REST endpoints to the Pydantic schemas defined in `apps/api/schemas/core.py`. It notes expected parameters, request/response bodies, and authentication assumptions so client stubs can be generated consistently alongside backend implementations.

## Users

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/users/` | List users (stubbed data for now). | Query: optional pagination (future). | _None_ | `User` | Authenticated app clients or internal bot.
| GET | `/users/{user_id}` | Fetch a user by ID. | Path: `user_id` (UUID/str). | _None_ | `User` | Authenticated.
| POST | `/users/` | Create a user record. | _None_ | `User` (id generated server-side). | `User` | Authenticated; restricted to admin/system.
| PUT/PATCH | `/users/{user_id}` | Update mutable user fields. | Path: `user_id`. | `User` (partial for PATCH). | `User` | Authenticated; self or admin.
| DELETE | `/users/{user_id}` | Soft-delete/deactivate a user. | Path: `user_id`. | _None_ | `User` (final state) | Authenticated; admin/system only.

## Linked Accounts

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/linked-accounts/` | List linked accounts for the current user or all (admin). | Query: `user_id` (optional). | _None_ | `LinkedAccount` | Authenticated.
| GET | `/linked-accounts/{linked_account_id}` | Fetch a linked account. | Path: `linked_account_id` (int). | _None_ | `LinkedAccount` | Authenticated; owner/admin.
| POST | `/linked-accounts/` | Create/link an external account (Spotify, Discord, Last.fm). | _None_ | `LinkedAccount` (no `id`, `created_at` provided). | `LinkedAccount` | Authenticated; owner only.
| DELETE | `/linked-accounts/{linked_account_id}` | Unlink a connected account. | Path: `linked_account_id`. | _None_ | `LinkedAccount` (final state) | Authenticated; owner/admin.

## Weeks

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/weeks/` | List club weeks (stubbed). | Query: optional pagination/status. | _None_ | `Week` | Public read.
| GET | `/weeks/{week_id}` | Fetch a single week. | Path: `week_id` (int). | _None_ | `Week` | Public read.
| POST | `/weeks/` | Create a week (planning/new cycle). | _None_ | `Week` (no `id/created_at`). | `Week` | Authenticated; admin/bot.
| PUT/PATCH | `/weeks/{week_id}` | Update week metadata or status. | Path: `week_id`. | `Week` (partial for PATCH). | `Week` | Authenticated; admin/bot.
| DELETE | `/weeks/{week_id}` | Remove/cancel a week. | Path: `week_id`. | _None_ | `Week` (final state) | Authenticated; admin/bot.

## Nominations

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/nominations/` | List nominations (stubbed). | Query: `week_id`, `user_id` optional. | _None_ | `Nomination` | Public read for archive; authenticated for current week.
| GET | `/nominations/{nomination_id}` | Fetch a nomination. | Path: `nomination_id` (int). | _None_ | `Nomination` | Public read for archive; authenticated for current week.
| POST | `/nominations/` | Submit a nomination. | _None_ | `Nomination` (no `id/submitted_at`). | `Nomination` | Authenticated; club participants/bot.
| PUT/PATCH | `/nominations/{nomination_id}` | Edit nomination notes/details before poll lock. | Path: `nomination_id`. | `Nomination` (partial for PATCH). | `Nomination` | Authenticated; owner/bot until locked.
| DELETE | `/nominations/{nomination_id}` | Withdraw a nomination before polls. | Path: `nomination_id`. | _None_ | `Nomination` (final state) | Authenticated; owner/admin/bot.

## Votes

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/votes/` | List votes (stubbed). | Query: `week_id` or `nomination_id`, optional `user_id`. | _None_ | `Vote` | Authenticated; bot/service.
| GET | `/votes/{vote_id}` | Fetch a vote. | Path: `vote_id` (int). | _None_ | `Vote` | Authenticated; voter/bot/admin.
| POST | `/votes/` | Cast a vote (1st/2nd choice rank). | _None_ | `Vote` (no `id/submitted_at`). | `Vote` | Authenticated; club participants/bot.
| PUT/PATCH | `/votes/{vote_id}` | Adjust a vote before polls close. | Path: `vote_id`. | `Vote` (partial for PATCH). | `Vote` | Authenticated; voter/bot until locked.
| DELETE | `/votes/{vote_id}` | Withdraw a vote before polls close. | Path: `vote_id`. | _None_ | `Vote` (final state) | Authenticated; voter/admin/bot.

## Ratings

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/ratings/` | List ratings (stubbed). | Query: `week_id`, `nomination_id`, `user_id` optional. | _None_ | `Rating` | Public read for archive; authenticated for active week.
| GET | `/ratings/{rating_id}` | Fetch a rating. | Path: `rating_id` (int). | _None_ | `Rating` | Public read for archive; authenticated for active week.
| POST | `/ratings/` | Submit a rating/review. | _None_ | `Rating` (no `id/created_at`). | `Rating` | Authenticated; club participants/bot.
| PUT/PATCH | `/ratings/{rating_id}` | Update rating/review before lock. | Path: `rating_id`. | `Rating` (partial for PATCH). | `Rating` | Authenticated; owner/bot until locked.
| DELETE | `/ratings/{rating_id}` | Remove a rating (e.g., spam or user request). | Path: `rating_id`. | _None_ | `Rating` (final state) | Authenticated; owner/admin/bot.

## Listen Events

| Method | Path | Description | Params | Request Body | Response Schema | Auth |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/listen-events/` | List listen events (stubbed). | Query: `user_id` required for user-level access; `since`/`until` optional. | _None_ | `ListenEvent` | Authenticated; user/worker/bot.
| GET | `/listen-events/{listen_event_id}` | Fetch a listen event. | Path: `listen_event_id` (int). | _None_ | `ListenEvent` | Authenticated; owner/admin.
| POST | `/listen-events/` | Ingest a listen event (real-time or batch). | _None_ | `ListenEvent` (no `id/ingested_at`). | `ListenEvent` | Authenticated; worker/bot.
| DELETE | `/listen-events/{listen_event_id}` | Remove an erroneous listen. | Path: `listen_event_id`. | _None_ | `ListenEvent` (final state) | Authenticated; owner/admin.
