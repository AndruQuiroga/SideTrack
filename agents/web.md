# agents/web.md — Web Frontend (Archive + Social)

## Purpose

Define tasks for building the **web frontend** that:

- Exposes a **public archive** of Sidetrack Club weeks and winners.
- Provides a **social music tracking experience** with profiles, feeds, and comparisons.
- Integrates with Spotify/Last.fm data via the backend API.
- Presents a sleek, modern, mobile-friendly UI.

Assume **Next.js + React + TailwindCSS** as the base stack.

---

## Context Highlights

From the high-level design:

- The site has two main faces:

  1. **Public Archive**
     - Winners gallery by week.
     - Week detail pages with nominees, poll results, ratings, and highlights.
  2. **Logged-in Social Tracker**
     - User profiles with listening and rating stats.
     - Friend/follow network.
     - Feeds, compatibility/profiles, and recommendations.

- The web app should **talk only to `apps/api`** (no direct DB or external APIs).

---

## Tasks

### web/init

**Goal:** Scaffold the Next.js app with base layout, routing, and Tailwind.

**Steps:**

1. Initialize `apps/web`:
   - Next.js app (preferably App Router).
   - TailwindCSS configured for dark theme support.

2. Set up basic layout:
   - Top nav (logo, nav links, sign-in/profile menu).
   - Content container and global typography styles.

3. Add a placeholder home page describing Sidetrack.

**Acceptance Criteria:**

- `pnpm dev:web` runs the site.
- Tailwind styles are applied and dark mode toggle (or auto dark) is in place.

---

### web/api-client

**Goal:** Provide a typed client for the backend API.

**Steps:**

1. Reuse `packages/shared` HTTP client where possible.
2. Implement functions for:
   - `listWeeks`, `getWeek(id)`
   - `getWeekRatings(id)`, `getWeekSummary(id)`
   - `getUserProfile(id/handle)`
   - `getUserTaste(id)`
   - `getCompatibility(a, b)`

3. Configure base URL via env (`NEXT_PUBLIC_API_BASE_URL`).

**Acceptance Criteria:**

- API client functions exist and are used in server components / hooks.
- Errors are handled gracefully (e.g., show friendly messages).

---

### web/archive/winners-gallery

**Goal:** Implement a public gallery for all weekly winners.

**UI Behavior:**

- Show a grid or list of cards, each representing a week:
  - Week label (e.g. `WEEK 003 [2025-11-24]`).
  - Album cover, title, artist.
  - Average rating (if available).
  - Tags (genre/decade/country) for quick scanning.

**Steps:**

1. Route: `/club` or `/weeks`.
2. Fetch `GET /club/weeks` from API.
3. Display cards with responsive layout and hover states.
4. Add basic filters/sorting:
   - Sort by date (newest first).
   - Filter by tag (genre/decade).

**Acceptance Criteria:**

- Visiting `/club` shows all weeks with correct data.
- Cards navigate to week detail pages.

---

### web/archive/week-detail

**Goal:** Build the detailed page for a single week.

**UI Sections:**

1. **Header:**
   - Week title & date.
   - Winner album: cover, title, artist, year.
   - Basic tags (genre/decade/country).
   - Spotify link.

2. **Poll Results:**
   - Ranked list of nominees with scores:
     - Points and rank.
     - Nominator name.
   - Visual representation (simple bar graph or ranking layout).

3. **Nominations:**
   - List of nominations:
     - Album, artist, nominator.
     - “Why?” pitch.
     - Pitch track link.

4. **Ratings:**
   - Average score + count.
   - Distribution (histogram or stacked bars).
   - Individual ratings:
     - User display name, stars, favorite track, short review.

5. **Meta:**
   - Links to Discord threads (if available): nominations, poll, ratings.

**Steps:**

1. Route: `/club/weeks/[id]`.
2. Fetch:
   - `GET /club/weeks/{id}` for summary.
   - `GET /club/weeks/{id}/ratings` if not included in detail.
3. Render all sections with clear design and spacing.

**Acceptance Criteria:**

- Page shows all the above sections using live API data.
- Handles missing data gracefully (e.g. week without ratings yet).

---

### web/auth-and-onboarding

**Goal:** Implement auth UI for signing in and connecting external accounts.

**Features:**

- Sign-in page:
  - Options for email/password or OAuth providers (Discord/Spotify).
- Settings / account page:
  - Connect/disconnect Spotify, Last.fm, Discord.
  - Show status of linked accounts and last sync times.

**Steps:**

1. Routing:
   - `/login`, `/signup`, `/settings`.
2. UI:
   - Simple forms or buttons for “Sign in with X”.
3. Integrate with API:
   - Use backend endpoints for auth.
   - Handle OAuth redirect flows (Next.js route for callbacks).

**Acceptance Criteria:**

- A user can sign in and access a protected profile page.
- Linked-service status is visible in settings.

---

### web/profile

**Goal:** Create user profile pages showing listening and rating stats.

**UI Sections:**

1. **Header:**
   - Avatar (from Discord/Spotify if available).
   - Display name / handle.
   - Badges (e.g. “Sidetrack Club Member”).

2. **Stats Overview:**
   - Top artists, albums, genres.
   - Simple stats like “tracks listened this week/last month”.

3. **Taste Visualization:**
   - Graph or chart from `TasteProfile`:
     - Mood/energy axes.
     - Genre distribution chart.

4. **Ratings & Reviews:**
   - List of albums the user has rated (club and personal).
   - Filtering by rating, date, or tag.

5. **Social:**
   - Follow/friend button.
   - Taste match score vs viewer (if viewer is another user).

**Steps:**

1. Route: `/u/[handleOrId]`.
2. Fetch:
   - `GET /users/{id}/summary`
   - `GET /users/{id}/taste`
   - `GET /users/{id}/ratings` (paginated).
3. Design UI using responsive cards and charts (e.g. with a React chart lib).

**Acceptance Criteria:**

- Visiting a profile shows stats and taste graphs with real data.
- Ratings list is scrollable and paginated if necessary.

---

### web/social/feed

**Goal:** Implement a feed showing recent activity from the user and their friends.

**Activity Types:**

- New rating posted.
- New album added to “completed” or “currently listening”.
- Significant listening milestones (optional).
- Club-related events (e.g. someone nominated/won).

**Steps:**

1. Route: `/feed`.
2. Fetch:
   - `GET /feed` (personalized, requires auth).
3. Present items as cards with:
   - Actor, action, target album/track, time.
   - Inline rating stars or summary.

**Acceptance Criteria:**

- Authenticated users see a feed with recent events from themselves and friends.
- Events link to relevant targets (profile or album/week page).

---

### web/social/compatibility

**Goal:** Let users view compatibility with friends and others.

**UI:**

- On a profile, show:
  - “Taste Match: XX%”.
  - Shared top artists, genres, and albums.
- Dedicated compare page:
  - Route: `/compare?userA=...&userB=...`.
  - Side-by-side taste charts.
  - Overlap lists and differences.

**Steps:**

1. Use API endpoint `GET /users/{user_a}/compatibility/{user_b}`.
2. Render:
   - Score prominently.
   - Shared artists as chips/tags.
   - Differences as interesting prompts (“They listen to more energetic stuff”).

**Acceptance Criteria:**

- Compatibility data loads and displays as described.
- For self vs self, show a trivial 100% state or disable the feature.

---

### web/listening-history

**Goal:** Show recent listening history and calendar-like views.

**UI Ideas:**

- A simple list of recent tracks with timestamps.
- A calendar heatmap showing days with lots of listening.
- Filter by source (Spotify / Last.fm).

**Steps:**

1. Route: `/u/[id]/listening`.
2. Fetch:
   - `GET /users/{id}/listens/recent`.
3. Display:
   - Group by day.
   - Show track names, albums, artists, and source.

**Acceptance Criteria:**

- Recent history loads.
- UI remains performant even with many entries (use pagination or infinite scroll).

---

### web/club-integration-hooks

**Goal:** Provide convenient links and prompts tying the web experience back to the Discord club.

**Features:**

- On week detail page:
  - Link to the live Discord thread (if accessible).
  - Indicate next scheduled discussion time.
- On profile:
  - Show the user’s history of club participation (weeks nominated, wins, ratings count).

**Acceptance Criteria:**

- Users can navigate from the web archive to the Discord experience via links.
- Club participation metrics are visible in relevant places.

---

### web/polish-and-theme

**Goal:** Make the site look “very very sleek, modern and easy to use” with a coherent visual identity.

**Tasks:**

- Define a color palette & typography scale.
- Improve album and profile cards:
  - Hover effects.
  - Skeleton loading states.
- Consistent iconography (e.g. for ratings, friends, play, etc.).
- Ensure mobile breakpoint layouts are pleasant.

**Acceptance Criteria:**

- UI is visually cohesive across pages.
- Components re-use shared styling primitives and layout patterns.
