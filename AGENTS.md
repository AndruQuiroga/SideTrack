# Sidetrack — Agents Overview

Welcome, agent. This repo defines the **Sidetrack** project: a unified system that:

1. Runs a weekly **Discord album club** (Sidetrack Club) end‑to‑end with a bot.
2. Publishes a **public web archive** of all weeks, winners, nominations, ratings, and discussion highlights.
3. Acts as a **social music tracking platform** with Spotify/Last.fm integration, mood/taste analysis, and friend/follow features.

This file gives you shared context and explains how the pieces fit together. Individual task documents for each subsystem live under `agents/` and contain concrete work items.

---

## 1. What Sidetrack Is

Sidetrack combines two things:

- A **Discord-based music club** where, each week:
  - Members nominate one album.
  - The group runs a **ranked vote** (1st and 2nd choice).
  - The winning album becomes “Album of the Week”.
  - Everyone listens, joins a scheduled discussion, and posts **ratings + short reviews**.

- A **web platform & tracker** where:
  - Anyone can **browse past club weeks**: winners, full nominee lists, tags, ratings, and comments.
  - Users can **connect Spotify / Last.fm** to import their listening history.
  - The system performs **taste/mood/genre analysis** and exposes social features:
    - Profiles, ratings, reviews.
    - Follow/friend relationships.
    - “Taste match” / compatibility comparisons.
    - Auto playlists and recommendations.

Think “Last.fm + AniList + Discord club automation” under one roof.

---

## 2. Core Goals

### 2.1 Club Automation Goals

- Automate the **full weekly club loop**:
  - Create nominations thread with a pinned mini‑form.
  - Close nominations at a deadline; open 1st/2nd choice polls.
  - Tally ranked votes and announce the winner.
  - Schedule & remind for the listening/discussion session.
  - Open and monitor a ratings thread, validating 1.0–5.0 scores and summarizing them.

- Store **all club data** in a central backend so the website can:
  - Show a gallery of weekly winners.
  - Show detailed pages per week with nominees, poll results, and ratings.
  - Compute stats over time (top nominators, genre trends, etc.).

### 2.2 Web Archive & Social Site Goals

- Build a **public site** (no login required to browse) with:
  - A **winners gallery**: one card per week (cover, title, artist, tags).
  - **Week detail pages**: album, nominator & pitch, nominees, poll results, ratings summary, and review excerpts.
  - **Filters/search** by genre, decade, country, nominator, artist, etc.

- Add **social music tracking**:
  - User profiles showing:
    - Top artists/albums/genres, temporal stats (this week / month / all‑time).
    - Ratings of albums (club picks and others).
    - Mood/taste visualizations derived from track features.
  - Friend/follow system:
    - See friends’ recent listens, ratings, and reviews.
    - “Taste match” score and overlap visualization between two users.
  - Optional **real-time flavor**:
    - “Now playing” display for connected Spotify users.
    - Light “listen along” affordances (e.g. quick link to open friend’s track on Spotify).

### 2.3 Analysis & Recommendations Goals

- Integrate **Spotify & Last.fm (and optionally ListenBrainz)**:
  - Import listening history (scrobbles / recently played).
  - Fetch audio features (energy, valence, tempo, danceability, etc.) from Spotify.
- Compute per‑user **taste fingerprints**:
  - E.g. axes like Energy, Happiness, Aggression, Acousticness, Danceability.
  - Histograms over genres, moods, and time of day.
- Use those fingerprints to:
  - Visualize users’ tastes on profile pages.
  - Compute user–user similarity (compatibility).
  - Suggest albums or tracks to explore (simple recommendation rules first; ML later).
  - Power friend‑blend playlists and mood‑based playlist generators.

---

## 3. High‑Level Architecture

The system is broken into several cooperative services:

- **`apps/bot` – Discord Bot**
  - Runs in the Sidetrack Club server.
  - Orchestrates the weekly album cycle (threads, polls, reminders, ratings).
  - Syncs all structured data (nominations, votes, ratings, schedule) to the backend API.

- **`apps/api` – Backend API**
  - Authoritative source of truth (PostgreSQL).
  - Manages users, linked accounts (Discord, Spotify, Last.fm), albums, tracks, listens, and taste profiles.
  - Exposes endpoints used by:
    - The Discord bot (club operations).
    - The web frontend (archive, profiles, social views).
    - Background workers (sync jobs, analysis orchestration).

- **`apps/web` – Web Frontend**
  - A sleek Next.js (or similar) app for:
    - Public club archive.
    - Authenticated social/music‑tracking experience.
  - Talks only to `apps/api` (no direct DB/external API access).

- **`apps/worker` – Background Jobs**
  - Periodically syncs listening data from Spotify/Last.fm.
  - Runs batch computations for stats, taste profiles, and recommendations.
  - Cleans up old data and handles slow/expensive tasks outside the request/response path.

- **`packages/shared` – Shared Libraries**
  - Shared TypeScript/Python types (e.g. data contracts for weeks, nominations, listens).
  - API client utilities for bot/web/worker.
  - Shared config and constants (e.g. rating scale, poll scoring).

- **External Systems**
  - **Discord API** – events, messages, threads, user IDs.
  - **Spotify API** – OAuth, playback state, audio features, playlist creation.
  - **Last.fm / ListenBrainz APIs** – scrobbles & charts.
  - **MusicBrainz (local or remote)** – canonical music metadata and search.

---

## 4. Core User Flows

### 4.1 Weekly Club Flow (Discord → API → Web)

1. **Nominations Phase**
   - Bot creates a **forum thread**: `WEEK 003 [2025‑11‑24] – NOMINATIONS`.
   - Posts a pinned mini‑form:
     - `album_name — artist_name (year)`
     - mini “Why?” pitch
     - one “pitch track” link
     - tags (Genre / Decade / Country)
   - Users reply with filled forms.
   - Bot parses replies, validates fields, and stores nominations via the API.

2. **Poll Phase**
   - At the nomination deadline, the bot:
     - Closes nominations (or simply stops accepting new ones).
     - Creates a **Poll thread** with two polls, or a 2‑slot voting interaction:
       - Poll 1: first‑choice vote.
       - Poll 2: second‑choice vote.
   - Scoring:
     - 1st place: 2 points.
     - 2nd place: 1 point.
     - Tie‑breaker: most 1st‑place votes.
   - Bot records each user’s selection and posts results to the API.

3. **Winner & Discussion**
   - Bot announces the winning album in a **Winner thread**, showing:
     - Album, artist, year, cover art.
     - Poll results and points.
     - Spotify link (and maybe other links).
   - Bot schedules and reminds for the listening/discussion session (date/time).

4. **Ratings Phase**
   - Bot opens a **Ratings thread** for the winning album with a pinned mini‑form.
   - Users post:
     - A score in the range 1.0–5.0 (half‑stars allowed).
     - Optional “favorite track” and final thoughts.
   - Bot parses ratings, validates the numeric value, and stores them via the API.
   - At the end, the bot posts an **aggregate summary**:
     - Average score, number of ratings, maybe a histogram.
   - Web archive surfaces all of this in a readable, attractive format.

### 4.2 Everyday Social & Tracking Flow (Spotify/Last.fm → Worker → API → Web)

1. **Account Setup**
   - User signs into the web app (email or OAuth).
   - Links external accounts (Spotify, Last.fm, Discord).
   - Grants permission for reading listening history and audio features.

2. **Passive Tracking**
   - Workers periodically fetch new scrobbles / recently played tracks.
   - Each listen is stored with time, track ID, and source.

3. **Taste Analysis**
   - For each new track (or periodically in batches):
     - Fetch audio features from Spotify or compute custom ones.
     - Update the user’s aggregate taste profile (e.g. mood vectors, genre distribution).
   - Store derived data (e.g. a “taste embedding” per user).

4. **Social Features**
   - Web shows:
     - Recent listens, top artists, top albums, genre breakdowns.
     - Friend feed: what friends recently played or rated.
     - “Taste match” between two users using similarity of taste embeddings and overlaps.
   - Recommendations and auto playlists use this data:
     - Friend‑blend playlists.
     - Mood‑based mixes.
     - “You and X both love Y, try Z next”.

---

## 5. Tech & Conventions (Assumptions)

These assumptions are here to align agents; they can be adjusted if needed, but stay consistent within a pass:

- **Language choices**
  - Backend/API: Python with FastAPI (preferred) or Node/TypeScript with a solid framework.
  - Bot: TypeScript (`discord.js`) or Python (`discord.py`), but keep it consistent with chosen stack.
  - Frontend: Next.js + React + TailwindCSS.
  - Workers: Same language as backend to share models and logic.

- **Data storage**
  - Primary DB: PostgreSQL.
  - Caching / queues: Redis.
  - Optional: separate DB instance or schema for MusicBrainz if mirrored.

- **Infra**
  - Docker for all services.
  - Local dev via `docker-compose` or similar.
  - Environment variables for secrets (no secrets in code).

- **Style**
  - Clear, typed interfaces for all API contracts.
  - Prefer small, focused modules and pure functions where possible.
  - Document new endpoints and data models as you add them.

---

## 6. Task Documents in `agents/`

Each subsystem has its own task document tailored for agents:

- `agents/core.md` — monorepo, env config, Docker, CI.
- `agents/api.md` — data models and API endpoints.
- `agents/bot.md` — Discord bot orchestration & sync.
- `agents/web.md` — Next.js frontend (archive + social UI).
- `agents/worker.md` — background jobs for sync and analysis.
- `agents/analysis.md` — taste profiling, similarity, recommendations.

Each file contains:

- A short **purpose & context** summary.
- A list of **tasks with IDs** (e.g. `api/club-weeks`, `bot/ratings-parser`).
- For each task:
  - Goal.
  - Inputs/context.
  - Steps or implementation hints.
  - Acceptance criteria.

Use the IDs when referring to tasks in commits or further prompts.

---

## 7. How Agents Should Use This Repo

1. **Start here** to understand the big picture (this file).
2. Jump into the relevant `agents/*.md` file for concrete tasks.
3. When completing a task:
   - Keep the described architecture and flows in mind.
   - Maintain alignment with shared types and API contracts.
4. If a task reveals missing context:
   - Update the corresponding `agents/*.md` with clarifications.
   - Make sure new endpoints or models are documented.

Your job as an agent is to move the system toward the goals in Sections 2–4 while keeping the codebase coherent and well‑documented. Focus on one task at a time, and treat the task docs as living specs you can refine as you go.
