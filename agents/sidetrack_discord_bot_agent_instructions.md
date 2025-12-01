# agents/bot.md — Sidetrack Discord Bot (MVP Instructions for Coding Agent)

> This spec tells a coding agent how to build the **Discord bot** for Sidetrack in `apps/bot`. It focuses on **intuitive UX**, **beautiful embedded cards**, and tight integration with the API + weekly club flow.

---

## 0. Scope & Goals

### 0.1. What this bot must do

The bot runs the **Sidetrack Club** flow inside Discord:

1. **Weeks**
   - Create/manage a “Week” (one club session).
   - Provide a clear overview card for each week.
2. **Nominations**
   - Collect album nominations via **slash commands + modals**.
   - Render nominations as **beautiful embeds (“cards”)**.
   - Sync nominations to the API.
3. **Polls (ranked 1st & 2nd choice)**
   - Open/close a ranked poll for a week.
   - Give users an intuitive **ballot UI** (buttons + select menus).
   - Record votes (1st = 2 pts, 2nd = 1 pt) in the API.
   - Announce the winner with a **highlight card**.
4. **Ratings**
   - Open ratings for the winning album.
   - Collect rating + mini-review via modal.
   - Show rating summaries as embeds.
5. **Quality-of-life**
   - Slash-based `/help`.
   - Clear error messages (ephemeral).
   - Respect permissions (only hosts can run admin commands).

**Out of scope for now**

- MCP; this is a **plain Node/TypeScript discord.js bot**, not an MCP server.
- Advanced scheduling (use manual commands for MVP; worker service can handle cron later).
- Complex moderation features.

---

## 1. Tech & Repo Assumptions

### 1.1. Stack

- Language: **TypeScript**.
- Library: **discord.js v14+**.
  - Use **slash commands + interactions** instead of prefix commands.
  - Use **embeds**, **buttons**, **select menus**, and **modals** for rich UI.
- Location: `apps/bot/` in the monorepo.
- Bot talks to **Sidetrack API** via HTTP using `SIDETRACK_API_BASE_URL` + `SIDETRACK_API_TOKEN`.

### 1.2. Environment variables

Required (MVP):

- `DISCORD_BOT_TOKEN`
- `DISCORD_CLIENT_ID`
- `DISCORD_GUILD_ID` (for fast, guild-scoped command registration during dev)
- `SIDETRACK_API_BASE_URL`
- `SIDETRACK_API_TOKEN`
- Optional:
  - `SIDETRACK_DEFAULT_CHANNEL_ID` (where week threads live)
  - `SIDETRACK_ROLE_HOST` (role allowed to run admin commands)

---

## 2. UX Principles & Discord Patterns

Use modern Discord UX best practices:

1. **Slash commands for discoverability**
   - All main actions are slash commands:
     - `/st-week start`, `/st-week overview`
     - `/st-nominate`
     - `/st-poll open`, `/st-poll close`
     - `/st-ratings open`, `/st-ratings summary`
2. **Embeds for “cards”**
   - Use `EmbedBuilder` to create **visually consistent cards**:
     - Title = album + artist or week label.
     - Thumbnail = album art.
     - Fields for nominator, tags, and links.
   - Follow patterns from embed guides and builders for attractive cards.
3. **Interactions for forms & votes**
   - **Modals** (`ModalBuilder`) for **nominations** and **ratings** so users get a focused form UI.
   - **Buttons + Select Menus** for **poll ballots** and quick actions.
4. **Threads for clutter-free rooms**
   - Each week gets a **thread**:
     - All nominations, poll, and ratings discussion live inside it.
5. **Ephemeral responses for errors & confirmations**
   - Errors, validation messages, and personal confirmations should be ephemeral.

**Important note on Polls:**  
Discord has **native polls** and a **Poll object** in the API, but support for bot-created polls and weighting is limited and focused on simple single-choice voting.
For Sidetrack’s **ranked 1st/2nd voting**, we will implement our **own poll UI** using embeds + components, similar to advanced poll bots like EasyPoll.

---

## 3. High-Level Flow

For a typical week:

1. Host runs `/st-week start` → bot:
   - Creates `Week` via API.
   - Creates a **week thread**.
   - Posts a **Week Overview** embed with “Nominate” button.
2. Users click “Nominate” → modal:
   - Album, artist, link, pitch, tags.
   - Bot calls API to register nomination.
   - Bot posts a **Nomination Card** embed in the thread.
3. Host runs `/st-poll open` when nominations close:
   - Bot fetches all nominations for the week.
   - Bot posts a **Poll Overview** embed with a “Open Ballot” button.
4. Users click “Open Ballot”:
   - Bot sends **ephemeral message** with one or two **select menus**:
     - Select 1st choice.
     - Select 2nd choice (optional, must be different).
   - Bot validates & stores vote via API.
5. Host runs `/st-poll close`:
   - API calculates results.
   - Bot posts a **Winner Announcement** embed + scoreboard.
   - Button: “Open Ratings”.
6. Host runs `/st-ratings open` (or uses button):
   - Bot posts a **Ratings Call** embed with “Rate this album” button.
   - Button opens rating modal.
7. Users submit ratings:
   - Rating (1.0–5.0 with halves) + fav track + short review.
   - Bot confirms ephemerally and optionally posts summary.
8. Host runs `/st-ratings summary`:
   - Bot fetches rating stats & posts **Week Summary** embed.

---

## 4. Implementation Roadmap (Tasks for Agent)

### 4.1. Core Bot Setup (`bot/setup-core`)

**Goal:** Get a clean, production-ready discord.js TS bot running in `apps/bot`.

**Steps:**

1. **Project structure**

   - `apps/bot/`
     - `src/index.ts` — entrypoint.
     - `src/config.ts` — env + constants.
     - `src/client.ts` — Discord client setup.
     - `src/commands/` — slash command handlers.
     - `src/interactions/` — component + modal handlers.
     - `src/embeds/` — embed/card builders.
     - `src/api/` — Sidetrack API client.
     - `src/logging.ts` — logger (pino or console wrapper).
     - `src/types.ts` — shared types.

2. **Discord client**

   - Create `Client` with required intents:
     - `Guilds`, `GuildMessages`, `GuildMembers`, `MessageContent` (if needed), `GuildMessageReactions`.
   - Register event listeners:
     - `ready`
     - `interactionCreate`
   - On `ready`, log bot tag + guild count.

3. **Command registration**

   - Create a `registerCommands.ts` script that:
     - Uses Discord REST API to upsert **guild commands** during dev.
     - Reads command metadata from `src/commands/**/*.ts`.

4. **Sidetrack API client**

   - `src/api/client.ts`:
     - Wrap `fetch`/`node-fetch` with base URL + auth header.
     - Provide typed helpers, for example:
       - `createWeek(payload)`
       - `getWeek(weekId)`
       - `listWeeks(params)`
       - `createNomination(weekId, payload)`
       - `listNominations(weekId)`
       - `createVote(weekId, payload)`
       - `closePoll(weekId)`
       - `createRating(weekId, payload)`
       - `getWeekSummary(weekId)`
   - Use the canonical data model for naming (`Week`, `Nomination`, `Vote`, `Rating`).

**Acceptance criteria**

- `pnpm --filter @sidetrack/bot run dev` connects the bot.
- `/ping` works and responds ephemerally.

---

### 4.2. Embed/Card System (`bot/embeds`)

**Goal:** Centralize all the “nice cards” used by the bot.

**Files:**

- `src/embeds/week.ts`
- `src/embeds/nomination.ts`
- `src/embeds/poll.ts`
- `src/embeds/ratings.ts`
- `src/embeds/common.ts` (colors, footer, icons)

**Design guidelines:**

- Use consistent **brand color** for `color` field (pull from UI docs if available).
- Always set:
  - `author` (Sidetrack Club)
  - `footer` (week number + year, maybe “Sidetrack Club”).
  - `timestamp` for key events.

**Functions (examples):**

- `buildWeekOverviewEmbed(week)`
- `buildNominationEmbed(nomination, albumMetadata)`
- `buildPollOverviewEmbed(week, nominations)`
- `buildPollResultsEmbed(week, results)`
- `buildWinnerEmbed(week, winner, results)`
- `buildRatingsCallEmbed(week, winner)`
- `buildRatingsSummaryEmbed(week, stats)`

**Album card layout suggestion:**

- `title`: `ALBUM — ARTIST`
- `description`: short pitch (truncated to ~200–300 chars).
- `thumbnail`: album art URL (from API/Spotify/Last.fm).
- `fields`:
  - `Nominated by`
  - `Tags` (genre / mood / custom)
  - `Year`, `Length`, `Source` (Spotify/MBID link)
- `url`: link to web week page (once web exists).

---

### 4.3. Week Management (`bot/week-lifecycle`)

#### `/st-week start`

**Goal:** Create a new week and its thread with a strong overview card.

**Flow:**

1. Validate caller has host permissions (role or user ID list).
2. Call API: `POST /weeks` with:
   - start date
   - phase = `nominations`
   - Discord context (channel ID, thread ID to be filled later).
3. Create a **thread** in a configured base channel:
   - Name: `Week {number}: {short descriptor}`.
4. Post **Week Overview** embed with:
   - Summary of phases.
   - Key dates (if provided or computed).
   - Buttons:
     - `Nominate an album` (`customId = "week:nominate:{weekId}"`)
     - `View nominations` (link to pinned message or same thread)
5. Pin the overview message in the thread.

#### `/st-week overview`

- Given `weekId` (or default to latest open week):
  - Fetch from API.
  - Post or update a **Week Overview** embed in current channel/thread.

**Acceptance criteria**

- Host can start a week; users see a clear “Nominate” button.
- Week thread exists and is pinned.

---

### 4.4. Nominations (`bot/nominations`)

We want nominations to feel like a **mini-form UI** with a rich card result.

#### Command & interaction surface

- Slash command: `/st-nominate [week]`
  - Optional `week` arg (defaults to current open week).
- Button: from Week Overview:
  - `customId = "week:nominate:{weekId}"`

Both surfaces open **the same modal**.

#### Modal: `Nominate album`

Use a **modal** with the following fields:

- `Album` (short text, required)
- `Artist` (short text, required)
- `Link (optional)` (Spotify, Bandcamp, etc.)
- `Pitch` (paragraph, required, ~500 char limit)
- `Tags (optional)` (comma-separated genres/moods)

#### Handling modal submit

1. Validate fields (basic length checks).
2. Call API: `POST /weeks/{weekId}/nominations`:
   - Include Discord user ID.
   - Include metadata fields.
3. Optional: API enriches with MusicBrainz/Spotify and returns:
   - Album art URL
   - Year, duration, canonical IDs
4. Bot posts a **Nomination Card** embed in the week thread:
   - Use `buildNominationEmbed`.
   - Add a small **“N” emoji prefix** in content to visually separate nominations.
5. Optionally reply ephemerally to the user:
   - “Nomination created!” + link to message.

#### Optional extras

- Add button on each nomination:
  - `Update nomination` (edit modal).
  - `Withdraw` (soft delete; API update).
- Limit 1–2 nominations per user (enforced via API, show friendly error).

**Acceptance criteria**

- Users can nominate via button or slash command.
- Each nomination produces a **single beautiful embed** with album art.
- All nominations for a week are visible in its thread.

---

### 4.5. Polls & Voting (`bot/polls`)

We implement a **custom ranked poll** (1st & 2nd choice) using components, not native polls.

#### `/st-poll open`

**Goal:** Start the poll for a given week.

**Flow:**

1. Ensure week is in `nominations` phase with nominations > 0.
2. API: mark week phase as `poll`.
3. Fetch nominations: `GET /weeks/{weekId}/nominations`.
4. Post a **Poll Overview** embed in the week thread:
   - Title: `Week {number} — Voting`
   - Description: “Pick your 1st & 2nd choice. 1st = 2 points, 2nd = 1 point.”
   - List nominations as numbered entries: `1) ALBUM — ARTIST (nominator)`.
   - Field: `Closes` (a timestamp or relative time).
5. Add action row with:
   - Button: `Open ballot` (`customId = "poll:open:{weekId}"`)

#### Ballot interaction (`poll:open:{weekId}`)

When user clicks “Open ballot”:

1. Send an **ephemeral message** with:
   - Two `StringSelectMenuBuilder`s:
     - `customId = "poll:first:{weekId}"`
     - `customId = "poll:second:{weekId}"`
   - Options:
     - `label`: `ALBUM — ARTIST`
     - `description`: truncated pitch or nominator.
     - `value`: nomination ID.
2. User selects:
   - 1st choice (required).
   - 2nd choice (optional).
3. “Submit ballot” button: `poll:submit:{weekId}`.
4. When user clicks Submit:
   - Validate they selected at least first.
   - Validate first != second (if both filled).
   - Call API: `POST /weeks/{weekId}/votes`:
     - `discord_user_id`
     - `first_nomination_id`
     - `second_nomination_id` (nullable)
   - API enforces one vote per user, updates existing if needed.
5. Reply ephemerally:
   - “Your ballot has been recorded.” + summarised choices.

#### `/st-poll close`

**Goal:** Close voting and announce the winner.

**Flow:**

1. Host-only, week must be in `poll` phase.
2. Call API: `POST /weeks/{weekId}/close-poll`:
   - Returns:
     - Winner nomination
     - Ranking w/ points
     - Ties info, etc.
   - Marks week phase as `discussion`.
3. Post two embeds in week thread:
   - **Winner Card** (big, prominent).
   - **Results Card** (scoreboard, top 3).
4. Add “Open ratings” button:
   - `customId = "ratings:open:{weekId}"`

**Acceptance criteria**

- Users cannot vote after `/st-poll close` (API rejects; bot shows error).
- Winner card clearly shows the album + who nominated it.
- Results card shows rank, points, # of 1st/2nd picks.

---

### 4.6. Ratings & Week Summary (`bot/ratings`)

#### `/st-ratings open` or button `ratings:open:{weekId}`

**Goal:** Announce ratings phase and provide an easy way to rate.

**Flow:**

1. Ensure week is in `discussion` or `ratings` phase.
2. Post a **Ratings Call** embed:
   - Title: `Rate: ALBUM — ARTIST`
   - Description:
     - “Rate from 1.0 to 5.0 (halves allowed).”
     - Mention expected mini-review length.
3. Add button: `Rate this album` (`ratings:rate:{weekId}`).

#### Rating modal (`ratings:rate:{weekId}`)

Modal `Rate Week {number}`:

- Fields:
  - `Score` (short text, e.g., `4.5`; validate 1.0–5.0, 0.5 steps).
  - `Favorite track` (short text, optional).
  - `Thoughts` (paragraph, optional, e.g., 0–500 chars).

On submit:

1. Validate score; show ephemeral error if invalid.
2. API: `POST /weeks/{weekId}/ratings`:
   - `discord_user_id`
   - `score`
   - `favorite_track`
   - `review`
3. Respond ephemerally with “Thanks for rating!”.
4. Optional: post a short public embed summarizing that rating.

#### `/st-ratings summary`

**Goal:** Summarize ratings in one or two nice cards.

**Flow:**

1. `GET /weeks/{weekId}/ratings/summary` returns:
   - Average, median, stddev.
   - Count, distribution (histogram).
   - Sample of short quotes.
2. Build **Ratings Summary** embed:
   - Show average rating prominently.
   - Show distribution (e.g., `⭐ 5.0: ###### (4)` style bar).
   - List 2–3 short quote snippets with user mention.

**Acceptance criteria**

- Users can rate only once (API can upsert; bot messages tell them if they updated).
- Summary card gives host a clear sense of reception.

---

### 4.7. Help & Safety (`bot/help-and-guardrails`)

#### `/st-help`

- Post a concise embed:
  - Explains weekly flow in 3–5 bullet steps.
  - Lists main commands.
  - Mentions thread usage & pinned overview.

#### Permissions

- Create a small utility to check if user is:
  - Server admin, or
  - Has `SIDETRACK_ROLE_HOST`, or
  - In a hardcoded allowed list.
- Use this check in:
  - `/st-week start`
  - `/st-poll open`
  - `/st-poll close`
  - `/st-ratings open`
  - `/st-ratings summary` (optional)

#### Error handling

- Wrap all command handlers in try/catch.
- On error:
  - Log full stack.
  - Show ephemeral friendly message to user.

---

## 5. Optional “Cool Features” (Future-Friendly Hooks)

These aren’t required for MVP, but the agent should structure code so these are easy to add:

1. **Auto-link to Web Archive**
   - Once `apps/web` has a public week page, use:
     - `url` on Week Overview, Winner, and Summary embeds to link there.

2. **Listening stats snippets**
   - For the winning album, show:
     - How many club members have scrobbled it.
     - Total plays and top listeners.
   - Use Last.fm or ListenBrainz via the API, not directly from bot.

3. **Role automation**
   - Add a “Club Participant” role for users who:
     - Nominated or voted or rated in a week.
   - Bot can assign/remove this role after each week.

4. **DM reminders**
   - Users can opt-in to DM reminders:
     - “Nominations closing soon.”
     - “Poll closing in 2 hours.”
   - Use worker + API to handle scheduling; bot just sends messages on command.

5. **Taste-match teaser**
   - Occasionally, in week summary, include:
     - A line like “Your closest taste-match this week: @User (⭐ 4.5 vs yours 4.0).”
   - Data comes from TasteProfile/compatibility engine via API.

---

## 6. Acceptance Checklist (MVP)

The bot is “done enough for MVP” when:

- [ ] `/st-week start` creates a week thread with overview embed + “Nominate” button.
- [ ] `/st-nominate` (or the Nominate button) opens a modal and posts a Nomination Card embed.
- [ ] `/st-poll open` produces a Poll Overview card with an “Open ballot” button.
- [ ] The “Open ballot” flow lets users submit 1st & 2nd choice via select menus and stores votes via the API.
- [ ] `/st-poll close` posts a Winner Card + Results Card and locks in the winner.
- [ ] `/st-ratings open` posts a Ratings Call embed + “Rate this album” button.
- [ ] The rating modal stores ratings correctly; `/st-ratings summary` posts a clear ratings summary.
- [ ] Only configured hosts can run week/poll/rating admin commands.
- [ ] All core embeds share a consistent, on-brand look and feel.

When this checklist is satisfied, save this spec as `agents/bot.md` (or equivalent) and keep it in sync as the bot evolves.

