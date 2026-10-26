# Rating creation and listen-event reads crash on the `metadata` alias

Not yet filed on GitHub; it needs the owner's approval, like issues #286 and #288.

Phase 3 authorization tests (`add-per-user-authorization`) reached two existing
defects that are present on main at d0a5102:

- `POST /weeks/{week_id}/ratings` raises `AttributeError: 'RatingCreate' object has
  no attribute 'metadata'` (`sidetrack/club/routes/ratings.py` reads
  `payload.metadata`; the field is `metadata_` with alias `metadata`). Every rating
  submission returns 500, so STATUS "Ratings and summary" is broken, not just
  untested.
- `GET /listen-events/` and `GET /listen-events/{id}` fail response validation
  whenever they return a row. `ListenEventRead` reads ORM attributes by alias, so
  `metadata` resolves to SQLAlchemy's `MetaData()` registry instead of the
  `metadata_` column.

Reproduce on migrated Postgres 16: rate a week's winning album as a member, or list
a user's listen events after inserting one. Expected: 201 and the stored row.
Actual: 500 with `request_id`.

Fix in a separate OpenSpec change with API regressions for both paths. The Phase 3
change does not touch these code paths. Its tests check authorization outcomes
that never serialize a listen event, and its omitted-`user_id` scenario uses a
nomination.
