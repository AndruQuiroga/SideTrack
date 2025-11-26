# agents/data-model.md — Domain Model & First-Pass Schema

## Purpose

Give agents a **clear mental model of the data** in Sidetrack:

- What the core entities are (users, albums, weeks, listens, etc.).
- How they relate (ERD-level overview).
- A **first-pass schema** in Python/SQLAlchemy + Pydantic that can be refined.
- Concrete cleanup/migration tasks to move from the existing repo to this model.

This file is the **source of truth for the domain model**. Other agent docs (API, workers, analysis, bot, web) should stay consistent with it.

---

## 1. Core Entities Overview

### User & LinkedAccount

- **User**
  - Represents a person on Sidetrack (web app identity).
  - May be linked to Discord, Spotify, Last.fm, ListenBrainz, etc.
  - Owns ratings, follows, and preferences.

- **LinkedAccount**
  - Represents a connection between a User and an external provider.
  - Providers (enum-ish): `discord`, `spotify`, `lastfm`, `listenbrainz`.
  - Holds provider-specific identifiers and tokens (where needed).

---

### Music Catalog: Album & Track

- **Album**
  - Canonical album entry.
  - Holds title, primary artist, year, external IDs (MusicBrainz, Spotify).
  - Used by both:
    - Club (nominations, winners, ratings).
    - Personal ratings and listening analysis.

- **Track**
  - Individual track entry, linked to one album.
  - Holds title, primary artist(s), duration, external IDs.
  - Used for listening events and track-level features.

---

### Club: Week, Nomination, Vote, Rating

- **Week**
  - One Sidetrack Club session (e.g. `WEEK 003 [2025-11-24]`).
  - Has dates (discussion time, deadlines).
  - Knows the winning album and relevant Discord thread IDs.

- **Nomination**
  - An album nominated by a user for a given Week.
  - Includes pitch text, a pitch track URL, and tags (Genre / Decade / Country).
  - Links: `Week` + `User` + `Album`.

- **Vote**
  - A ranked vote (1st/2nd choice) by a user for a nomination in a Week.
  - Each user can cast at most one 1st and one 2nd vote per Week.
  - Scoring: rank 1 → 2 points, rank 2 → 1 point.

- **Rating**
  - A 1.0–5.0 rating (half increments allowed) of the Week’s winning album.
  - Also includes optional favorite track and freeform review text.
  - Typically connected to a Week + Album + User.

---

### Listening & Analysis: ListenEvent, TrackFeatures, TasteProfile

- **ListenEvent**
  - A single instance of a user listening to a track at a given timestamp.
  - Stored for both club-related and general listening history.
  - Source: `spotify`, `lastfm`, `listenbrainz`, etc.

- **TrackFeatures**
  - Per-track audio features used in analysis:
    - Energy, valence, danceability, tempo, acousticness, etc.
  - Derived mostly from Spotify’s audio features or ML models.

- **TasteProfile**
  - Aggregated view of a user’s taste over time.
  - Includes genre distribution, feature averages, and optional temporal patterns.

---

### Social: Follow, Compatibility, UserRecommendations

- **Follow**
  - Relationship where User A follows User B.

- **Compatibility**
  - Cached pair-wise taste similarity between two users.
  - Derived from TasteProfile and overlap in artists/albums.

- **UserRecommendations**
  - Precomputed recommendations for a user:
    - Candidate albums + score + reason string.

---

## 2. Relationships (ERD Sketch)

Textual ERD sketch (primary keys omitted for brevity):

- `User` 1—N `LinkedAccount`
- `User` 1—N `Nomination`
- `User` 1—N `Vote`
- `User` 1—N `Rating`
- `User` 1—N `ListenEvent`
- `User` 1—1 `TasteProfile` (per time scope, or 1 active)
- `User` N—N `User` via `Follow` (follower/followee)

- `Album` 1—N `Track`
- `Album` 1—N `Nomination`
- `Album` 1—N `Rating`
- `Album` 1—N `ListenEvent` (through Track)
- `Album` N—N `GenreTag` (if normalized)

- `Track` 1—N `ListenEvent`
- `Track` 1—1 `TrackFeatures` (or 1—N with versions)

- `Week` 1—N `Nomination`
- `Week` 1—N `Vote`
- `Week` 1—N `Rating`
- `Week` 1—1 `Album` as winner

- `UserCompatibility` / `Compatibility` is between pairs of Users.
- `UserRecommendations` 1—N recommended albums per User.

Simple ASCII sketch:

```text
User --< LinkedAccount
User --< Nomination >-- Album
User --< Vote >-- Nomination >-- Week
User --< Rating >-- Album
User --< ListenEvent >-- Track >-- Album

User --< Follow >-- User
User --< UserRecommendations >-- Album
User --< Compatibility >-- User

Track --< ListenEvent
Track -- TrackFeatures
User -- TasteProfile
```

This is the conceptual map agents should keep in mind when working on API, worker, analysis, and web layers.

---

## 3. First-Pass SQLAlchemy + Pydantic Models

> These are **starting-point drafts**. Agents generating code should refine them (naming, typing, indexing) but try to stay close to these semantics.

Assume:

- SQLAlchemy 2.0 style (declarative with type hints).
- Pydantic v2 style models for API schemas.
- UUID primary keys where sensible.

### 3.1 User & LinkedAccount

```python
# apps/api/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    linked_accounts: Mapped[list["LinkedAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
```

```python
from enum import Enum as PyEnum

class ProviderType(str, PyEnum):
    DISCORD = "discord"
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"


class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[ProviderType] = mapped_column(Enum(ProviderType), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # tokens for Spotify / Last.fm
    access_token: Mapped[str | None] = mapped_column(String(4096))
    refresh_token: Mapped[str | None] = mapped_column(String(4096))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="linked_accounts")
```

Pydantic read models (first pass):

```python
# apps/api/schemas/user.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum


class ProviderType(str, Enum):
    discord = "discord"
    spotify = "spotify"
    lastfm = "lastfm"
    listenbrainz = "listenbrainz"


class LinkedAccountRead(BaseModel):
    id: UUID
    provider: ProviderType
    provider_user_id: str

    class Config:
        from_attributes = True


class UserRead(BaseModel):
    id: UUID
    display_name: str
    handle: str | None = None
    created_at: datetime
    linked_accounts: list[LinkedAccountRead] = []

    class Config:
        from_attributes = True
```

---

### 3.2 Album & Track

```python
# apps/api/models/music.py
from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

class Album(Base):
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    release_year: Mapped[int | None] = mapped_column(Integer)

    musicbrainz_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    spotify_id: Mapped[str | None] = mapped_column(String(64), unique=True)

    cover_url: Mapped[str | None] = mapped_column(Text)

    tracks: Mapped[list["Track"]] = relationship(back_populates="album")
```

```python
class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    musicbrainz_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    spotify_id: Mapped[str | None] = mapped_column(String(64), unique=True)

    album: Mapped["Album"] = relationship(back_populates="tracks")
```

---

### 3.3 Week, Nomination, Vote, Rating

```python
# apps/api/models/club.py
from sqlalchemy import DateTime, Boolean, Float, UniqueConstraint

class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "WEEK 003 [2025-11-24]"
    week_number: Mapped[int | None] = mapped_column(Integer)
    discussion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    nominations_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    poll_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    winner_album_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id")
    )

    # Optional Discord IDs
    nominations_thread_id: Mapped[int | None] = mapped_column()
    poll_thread_id: Mapped[int | None] = mapped_column()
    winner_thread_id: Mapped[int | None] = mapped_column()
    ratings_thread_id: Mapped[int | None] = mapped_column()

    winner_album: Mapped["Album"] = relationship()
```

```python
class Nomination(Base):
    __tablename__ = "nominations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )

    pitch: Mapped[str | None] = mapped_column(Text)
    pitch_track_url: Mapped[str | None] = mapped_column(Text)

    # Simple tags representation; can later be normalized
    genre: Mapped[str | None] = mapped_column(String(64))
    decade: Mapped[str | None] = mapped_column(String(16))
    country: Mapped[str | None] = mapped_column(String(64))

    user: Mapped["User"] = relationship()
    week: Mapped["Week"] = relationship()
    album: Mapped["Album"] = relationship()
```

```python
class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("week_id", "user_id", "rank", name="uq_vote_week_user_rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    nomination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nominations.id", ondelete="CASCADE"), nullable=False
    )

    rank: Mapped[int] = mapped_column(Integer)  # 1 or 2

    week: Mapped["Week"] = relationship()
    user: Mapped["User"] = relationship()
    nomination: Mapped["Nomination"] = relationship()
```

```python
class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("week_id", "user_id", name="uq_rating_week_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    week_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )

    value: Mapped[float] = mapped_column(Float, nullable=False)  # 1.0–5.0
    favorite_track: Mapped[str | None] = mapped_column(String(255))
    review: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship()
    week: Mapped["Week"] = relationship()
    album: Mapped["Album"] = relationship()
```

---

### 3.4 ListenEvent, TrackFeatures, TasteProfile

```python
# apps/api/models/listening.py
from sqlalchemy import Enum as SAEnum

class ListenSource(str, PyEnum):
    SPOTIFY = "spotify"
    LASTFM = "lastfm"
    LISTENBRAINZ = "listenbrainz"


class ListenEvent(Base):
    __tablename__ = "listen_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False
    )

    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[ListenSource] = mapped_column(SAEnum(ListenSource), nullable=False)

    user: Mapped["User"] = relationship()
    track: Mapped["Track"] = relationship()
```

```python
class TrackFeatures(Base):
    __tablename__ = "track_features"

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )

    energy: Mapped[float | None] = mapped_column(Float)
    valence: Mapped[float | None] = mapped_column(Float)
    danceability: Mapped[float | None] = mapped_column(Float)
    tempo: Mapped[float | None] = mapped_column(Float)
    acousticness: Mapped[float | None] = mapped_column(Float)
    instrumentalness: Mapped[float | None] = mapped_column(Float)

    track: Mapped["Track"] = relationship()
```

```python
from sqlalchemy.dialects.postgresql import JSONB

class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    genre_histogram: Mapped[dict | None] = mapped_column(JSONB)
    feature_means: Mapped[dict | None] = mapped_column(JSONB)
    time_of_day_histogram: Mapped[dict | None] = mapped_column(JSONB)

    last_computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()
```

---

### 3.5 Social: Follow, Compatibility, UserRecommendations

```python
# apps/api/models/social.py

class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followee_id", name="uq_follow_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    followee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
```

```python
class Compatibility(Base):
    __tablename__ = "compatibilities"
    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_compat_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0–100
    payload: Mapped[dict | None] = mapped_column(JSONB)  # overlap details, etc.
```

```python
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
```

---

## 4. Migration & Cleanup Tasks for the Existing Repo

These tasks are specifically for **cleaning up the current codebase** and aligning it with this data model.

### data-model/audit-existing-schema

**Goal:** Inventory existing DB tables and ORM models, and map them to the new conceptual model.

**Steps:**

1. Enumerate current models/tables:
   - Note names, key fields, and relationships.
2. For each:
   - Map each to one of the new entities (User, Week, Nomination, etc.) or mark as deprecated.
3. Capture this mapping in a short markdown table in `docs/legacy-mapping.md`.

**Acceptance Criteria:**

- There is a written mapping of “old → new” for all tables/models.
- No legacy entity is left unexplained.

---

### data-model/introduce-new-tables-phase1

**Goal:** Add new tables side-by-side with existing ones without breaking current functionality.

**Steps:**

1. Add SQLAlchemy models & migrations for:
   - User, LinkedAccount, Album, Track (if not already aligned).
   - Week, Nomination, Vote, Rating.
   - ListenEvent, TrackFeatures, TasteProfile.

2. Ensure names & constraints match the first-pass definitions here (or documented deviations).

**Acceptance Criteria:**

- New tables exist in the DB.
- Old features still work (we haven’t removed legacy tables yet).

---

### data-model/migrate-data-phase2

**Goal:** Migrate data from legacy tables to new schema.

**Steps:**

1. Write migration scripts or one-off data migration jobs:
   - Port existing users to `User`.
   - Port any existing Discord/Spotify IDs into `LinkedAccount`.
   - Map existing club weeks/nominations/ratings into `Week`, `Nomination`, `Rating`.
   - Map existing listening history (if any) into `ListenEvent`.

2. Run migrations carefully in a staging environment and verify:
   - Record counts.
   - Data integrity (FKs, unique constraints).

**Acceptance Criteria:**

- Most historical data is represented correctly in the new schema.
- Spot checks show no obvious mismatches.

---

### data-model/deprecate-legacy

**Goal:** Remove unused/legacy tables and fields once new model is adopted.

**Steps:**

1. Once API and web are using new models:
   - Identify tables/columns no longer referenced.
2. Add migrations to drop them.
3. Remove corresponding ORM models and code paths.

**Acceptance Criteria:**

- Codebase does not reference legacy tables/models.
- Schema is clean and matches the conceptual model in this file.

---

### data-model/indexing-and-performance-pass

**Goal:** Add appropriate indexes and adjust fields for performance once usage patterns are observed.

**Steps:**

1. Based on real queries (API, workers):
   - Add composite indexes where needed (e.g. on `ListenEvent(user_id, played_at)`).
2. Optimize types:
   - Confirm that text fields and JSONB usage are appropriate.
3. Document any non-obvious indexing choices here or in a `DB_NOTES.md`.

**Acceptance Criteria:**

- Common queries run efficiently in staging.
- No obviously missing indexes for high-volume tables.

---

Agents working on the API, workers, or cleanup should read this file before designing new models or migrations. This is the **canonical domain model** and should be updated if we discover better normalizations or necessary changes. 
