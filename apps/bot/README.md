# Sidetrack Discord Bot

The Sidetrack Discord bot orchestrates the weekly album club cycle including nominations, voting, winner announcements, and ratings. It provides a rich user experience with modals, buttons, select menus, and beautiful embed cards.

## Commands

### User Commands

- `/ping` — Check if the bot is online.
- `/st-nominate` — Open a modal to nominate an album for the current week.
- `/st-week overview` — Display the current week's status and nomination button.
- `/st-ratings summary` — Show the ratings summary for the winning album.
- `/st-help` — Display help information about the bot and weekly flow.

### Admin Commands

These require `Manage Server` permission or an admin role:

- `/st-week start` — Create a new week and open a nominations thread with an overview embed.
- `/st-poll open` — Start voting on the nominations.
- `/st-poll close` — Close voting and announce the winner.
- `/st-ratings open` — Open the ratings phase for the winning album.

### Legacy Commands

- `/week-start` — Deprecated alias for `/st-week start`.

## Interactive Features

### Buttons

- **Nominate an Album** — Opens the nomination modal.
- **Open Ballot** — Opens the voting interface with select menus.
- **Submit Ballot** — Submits your 1st and 2nd choice votes.
- **Rate This Album** — Opens the rating modal.
- **Refresh** — Refreshes the week overview.
- **Open Ratings** — Opens the ratings phase after poll closes.

### Modals

- **Nomination Form** — Album, Artist, Pitch, Link (optional), Tags (optional).
- **Rating Form** — Score (1.0-5.0), Favorite Track (optional), Thoughts (optional).

### Select Menus

- **1st Choice** — Select your first choice nomination (2 points).
- **2nd Choice** — Select your second choice nomination (1 point).

## Voting System

- 1st choice = 2 points
- 2nd choice = 1 point
- Highest total wins; ties broken by most 1st-place votes.

## Configuration

The bot reads configuration from environment variables:

### Required

- `SIDETRACK_API_BASE_URL` — API base URL.
- `SIDETRACK_API_TOKEN` — Bot auth token for the API.
- `DISCORD_BOT_TOKEN` — Discord bot token.
- `SIDETRACK_NOMINATIONS_FORUM_ID` — Forum channel ID for nomination threads.

### Recommended

- `DISCORD_CLIENT_ID` — For slash command registration.
- `DISCORD_GUILD_ID` — For guild-scoped command registration.

### Optional

- `SIDETRACK_ADMIN_ROLE_IDS` — Comma-separated role IDs allowed to run admin commands.

### Retry Configuration

- `SIDETRACK_RETRY_ATTEMPTS` — Number of retry attempts (default: 3).
- `SIDETRACK_RETRY_DELAY_MS` — Base delay between retries (default: 250ms).

## Weekly Flow

1. **Admin runs `/st-week start`** → Creates week and nominations thread.
2. **Users click "Nominate an Album"** → Fill modal → Nomination card posted.
3. **Admin runs `/st-poll open`** → Poll overview with "Open Ballot" button.
4. **Users click "Open Ballot"** → Select 1st & 2nd choice → Submit.
5. **Admin runs `/st-poll close`** → Winner announced + results.
6. **Admin runs `/st-ratings open`** → Rating call with "Rate" button.
7. **Users click "Rate This Album"** → Fill rating modal.
8. **Anyone runs `/st-ratings summary`** → See aggregated ratings.

## Reminders

The bot schedules automatic reminders:

- 1 hour before nominations close.
- When nominations close.

## Message Parsing

The bot also listens for messages in nomination threads and parses mini-form format:

```
Album — Artist (Year)
Why?: <pitch>
Pitch track: <URL>
Tags: <genre / decade / country>
```

This allows users to nominate via message as an alternative to the modal.
