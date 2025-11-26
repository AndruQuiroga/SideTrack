# agents/bot.md — Discord Bot for Sidetrack Club

## Purpose

Define tasks for implementing the **Discord bot** that runs the Sidetrack Club inside a Discord server, including:

- Automated weekly workflow (nominations → poll → winner → ratings).
- Rich embeds and mini-forms.
- Integration with the backend API.
- Reminders and admin controls.

Assume use of **discord.js (TypeScript)** or **discord.py (Python)**. Align structure and config with monorepo and API.

---

## Context Highlights

From the high-level design:

- Bot manages **four main phases** each week:
  1. NOMINATIONS
  2. POLL (ranked: 1st & 2nd)
  3. WINNER ANNOUNCEMENT & DISCUSSION SCHEDULING
  4. RATINGS

- Each phase lives in a dedicated **forum thread** or channel section, with a pinned mini-form.
- Bot parses messages, validates forms, and syncs the data to the API so the web archive always reflects the current state.
- Bot knows about:
  - The current week object (fetched/created via the API).
  - Config for which forum/channel to use.
  - Cutoff dates/times for phases.

---

## Tasks

### bot/setup

**Goal:** Scaffold the bot app, connect to Discord, and set up basic configuration.

**Steps:**

1. Initialize `apps/bot`:
   - Bot entrypoint (e.g. `src/index.ts` or `bot/main.py`).
   - Load `DISCORD_TOKEN` and any guild/channel IDs from env.
   - Connect to Discord and log a “ready” message.

2. Implement basic handlers:
   - Slash command `/ping` that replies with “Pong (Sidetrack is online)”.
   - Error handling/logging.

3. Add structured config:
   - JSON or TS/Python config mapping:
     - `guild_id`
     - `forum_channel_id` or separate IDs for nomination/poll/winner/rating categories.
   - Expose a way to override these via env for different servers.

**Acceptance Criteria:**

- Bot can start locally, log in, and respond to `/ping`.
- Config is not hard-coded; uses env and/or config files.

---

### bot/club-lifecycle

**Goal:** Implement the logic for starting and managing a weekly cycle.

**Responsibilities:**

- Create threads for:
  - NOMINATIONS.
  - POLL.
  - WINNER.
  - RATINGS.

- Label threads with week number and date.

**Steps:**

1. Define a `WeekConfig` structure:
   - Week label, dates for each phase (nomination close, poll close, discussion time).
   - Possibly generated from a schedule or created by a mod command.

2. Provide **admin/mod command**:
   - `/week start <date>` or `/week create`:
     - Calls API to create a `Week`.
     - Creates the **NOMINATIONS** thread with pinned mini-form.
     - Stores mapping: Week ID ↔ Discord thread IDs via API (e.g. `ThreadRef`).

3. Optionally, support a **scheduled job** to auto-create weeks based on a recurring rule (e.g. every Monday).

**Acceptance Criteria:**

- Mod can run a command that:
  - Creates a new week record via API.
  - Creates a NOMINATIONS thread with correct title and pinned instructions.
- Thread IDs are persisted to backend for later use.

---

### bot/nominations-parser

**Goal:** Parse nomination messages and sync them to the API.

**Context:**

- Users post nominations using a mini-form like:

  ```text
  album_name — artist_name (year)
  Why?: ...
  Pitch track (choose one): ...
  Tags (Genre / Decade / Country): ...
  ```

**Steps:**

1. Listen for messages in the NOMINATIONS thread for the active week.
2. For each message:
   - Ignore bot messages.
   - Parse the form:
     - Extract album, artist, year.
     - Extract “Why?” as pitch.
     - Extract pitch track URL.
     - Extract tags (split on `/` or commas).
   - Validate (basic sanity checks).

3. Call `/club/weeks/{week_id}/nominations` API:
   - Send parsed values plus Discord user ID.

4. React to the message (e.g. ✅) when successfully parsed & saved.
5. Handle updates/re-parsing if user edits their message before the deadline (if desired).

**Acceptance Criteria:**

- Nominations appear in DB after posting mini-forms.
- Errors (bad formatting) are logged and optionally responded to with a gentle error message.

---

### bot/polls

**Goal:** Implement ranked voting via Discord, and sync votes to the API.

**Options:**

- Use two native Discord polls (if available via API).
- Or implement a custom scheme using reactions/buttons/menus.

**Steps (suggested):**

1. When nomination phase closes:
   - Bot fetches nominations for the week via API.
   - Bot posts a POLL thread:
     - Top message lists nominees with codes/emojis.
     - Bot creates two polls:
       - Poll 1: “First Choice”.
       - Poll 2: “Second Choice”.

2. Listen for poll interactions:
   - For each user’s selection in each poll:
     - Map back to `Nomination`.
     - Call `/club/weeks/{week_id}/votes` with rank 1 or 2.
     - Enforce rules:
       - Only one vote per rank per user.
       - Prevent voting for yourself if that’s a rule.

3. At poll close:
   - Call `/club/weeks/{week_id}/votes/summary`.
   - Post an embed summarizing poll results: points, ranks, tiebreaker notes.

**Acceptance Criteria:**

- Bot correctly records first and second choices per user.
- Summary in Discord matches API summary.
- No duplicate or conflicting votes per user/rank.

---

### bot/winner-announcement

**Goal:** Announce the winning album and create the Winner/Discussion thread.

**Steps:**

1. After polling is done:
   - Bot gets the winner from `/votes/summary` or from a dedicated API endpoint.
   - Bot updates the `Week` with `winner_album_id` (if API requires explicit call).

2. Create a **Winner** thread:
   - Title: `WEEK 003 [2025-11-24] - WINNER - <Album> — <Artist> (Year)`.
   - Embed includes:
     - Album cover.
     - Poll results (1st/2nd/3rd place).
     - Spotify link.
     - Discussion time and voice channel.

3. Store thread ID to the API for linking.

**Acceptance Criteria:**

- Winner thread is created with correct information.
- Web week detail page reflects the same winner/poll summary.

---

### bot/ratings-parser

**Goal:** Parse rating mini-forms and sync ratings to API.

**Context:**

- Ratings thread mini-form:

  ```text
  Rating (1.0–5.0):
  Favorite track (opt):
  final thoughts (opt):
  ```

**Steps:**

1. Listen for messages in RATINGS thread for active week.
2. For each message:
   - Parse rating value; ensure 1.0–5.0 with .5 steps accepted.
   - Extract favorite track and review text.
3. Call `/club/weeks/{week_id}/ratings`:
   - Provide Discord user ID, rating, favorite track, review.
4. React (e.g. ⭐) to confirm.
5. Optionally, on rating edits, update rating in API.

6. When ratings close:
   - Optionally invoke `/ratings/summary` and post recap embed with:
     - Average rating.
     - Count.
     - Maybe a text histogram.

**Acceptance Criteria:**

- Ratings from Discord thread appear correctly in web UI.
- Malformed ratings are rejected or flagged without breaking the bot.

---

### bot/reminders-and-schedule

**Goal:** Provide scheduled reminders and automatic phase transitions.

**Responsibilities:**

- Remind users:
  - X hours before nominations close.
  - X hours before polls close.
  - Before discussion start.
  - Optional reminder to rate the album.

- Trigger:
  - Poll creation at nomination deadline.
  - Winner announcement at poll deadline.
  - Rating thread creation at discussion time.

**Steps:**

1. Choose a scheduler strategy:
   - Cron-like library (e.g. `node-cron`) or an in-process schedule that re-syncs with API at startup.
2. Store important timestamps in the `Week` record.
3. On startup:
   - Fetch upcoming weeks and schedule jobs.
4. Job actions:
   - Send reminder messages to relevant threads.
   - Trigger phase-creation commands (poll, ratings thread).

**Acceptance Criteria:**

- Reminders appear at correct times.
- Phase transitions are automated when timestamps are defined.

---

### bot/api-client

**Goal:** Provide a clean, typed client for calling the backend from the bot.

**Steps:**

1. Reuse `packages/shared` HTTP client where available.
2. Create functions:
   - `getOrCreateWeek(...)`
   - `postNomination(...)`
   - `postVote(...)`
   - `postRating(...)`
   - `getWeekSummary(...)`
3. Handle auth:
   - Use a bot-specific API key via env.
   - Attach to `Authorization` header.

**Acceptance Criteria:**

- Bot code calls the API via the client module, not via raw fetch/requests scattershot.
- Errors from API are logged clearly and don’t crash the bot.

---

### bot/admin-commands

**Goal:** Give organizers minimal control commands.

**Examples:**

- `/week start` — manually start a new week.
- `/week resync` — re-scan nomination or rating threads.
- `/week summary` — post a summary message.

**Acceptance Criteria:**

- Commands are visible only to authorized roles.
- Help text or `/help` explains commands succinctly.
