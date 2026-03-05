# Sidetrack Club Bot -- User Guide

This guide explains how to use the Sidetrack Club Discord bot as a member or admin.

---

## Table of Contents

- [Overview](#overview)
- [Weekly Flow](#weekly-flow)
- [For Members](#for-members)
  - [Nominating an Album](#nominating-an-album)
  - [Voting](#voting)
  - [Rating the Winner](#rating-the-winner)
  - [Viewing Results](#viewing-results)
- [For Admins](#for-admins)
  - [Starting a New Week](#starting-a-new-week)
  - [Opening the Poll](#opening-the-poll)
  - [Closing the Poll](#closing-the-poll-and-announcing-the-winner)
  - [Opening Ratings](#opening-ratings)
- [Command Reference](#command-reference)
- [Scoring and Tiebreakers](#scoring-and-tiebreakers)
- [Rating Rules](#rating-rules)
- [Troubleshooting](#troubleshooting)

---

## Overview

Sidetrack Club is a weekly album club. Each week follows the same loop:

1. **Nominations** -- members nominate albums they want the group to listen to.
2. **Voting** -- members vote for their 1st and 2nd choice from the nominees.
3. **Winner** -- votes are tallied and the winning album is announced.
4. **Ratings** -- everyone listens to the winning album, then submits a score and review.

The bot handles every step. All activity happens in forum threads that the bot
creates automatically.

---

## Weekly Flow

```
 Nominations       Voting         Winner          Ratings
 ──────────── -> ──────────── -> ──────────── -> ────────────
  Members post     Members pick   Bot announces   Members post
  album picks      1st & 2nd      the winner      scores &
  via button       choice via     and results     reviews
  or mini-form     ballot
```

---

## For Members

### Nominating an Album

When a new week starts, the bot creates a **Nominations** thread in the forum.
You can nominate in two ways:

#### Option A: Button (recommended)

1. Find the pinned overview message in the nominations thread.
2. Click the **"Nominate an Album"** button.
3. A form pops up with these fields:

| Field                 | Required | Details                                                              |
| --------------------- | -------- | -------------------------------------------------------------------- |
| Album Title           | Yes      | The album name (max 200 characters)                                  |
| Artist                | Yes      | The artist or band name (max 200 characters)                         |
| Why should we listen? | Yes      | Your pitch for the album (max 500 characters)                        |
| Link                  | No       | A Spotify, Bandcamp, or other URL to the album                       |
| Tags                  | No       | Genre, decade, and country separated by `/` (e.g. `rock / 90s / UK`) |

4. Submit the form. You'll get a private confirmation, and the bot posts your
   nomination card publicly in the thread.

#### Option B: Text mini-form

Post a message in the nominations thread using this format:

```
Album -- Artist (Year)
Why?: Your pitch for the album goes here
Pitch track: https://open.spotify.com/track/...
Tags: genre / decade / country
```

The bot will parse your message and react with a checkmark on success.

**Rules:**

- The `Album -- Artist` line is required. Year in parentheses is optional.
- The `Why?:` pitch line is required.
- `Pitch track:` and `Tags:` lines are optional.

---

### Voting

When an admin opens the poll, the bot posts a list of all nominations with an
**"Open Ballot"** button.

1. Click **"Open Ballot"**. A private ballot appears (only you can see it).
2. Use the **1st Choice** dropdown to pick your top album (worth 2 points).
3. Use the **2nd Choice** dropdown to pick your runner-up (worth 1 point). This
   is optional.
4. Click **"Submit Ballot"**.

**Rules:**

- You must select at least your 1st choice.
- Your 1st and 2nd choice cannot be the same album.
- Your ballot is private -- no one else can see your picks until results are
  announced.
- Ballots expire after 30 minutes of inactivity. If yours expires, click "Open
  Ballot" again.

---

### Rating the Winner

After the winner is announced and ratings are opened, the bot creates a
**Ratings** thread and posts a "Rate This Album" prompt.

#### Option A: Button (recommended)

1. Click **"Rate This Album"**.
2. A form pops up with these fields:

| Field          | Required | Details                                  |
| -------------- | -------- | ---------------------------------------- |
| Score          | Yes      | A number from 1.0 to 5.0 (e.g. `3.5`)    |
| Favorite Track | No       | Name of your favorite track on the album |
| Thoughts       | No       | A short review (max 500 characters)      |

3. Submit. Scores are rounded to the nearest half-star (e.g. 3.7 becomes 3.5).

#### Option B: Text mini-form

Post a message in the ratings thread using this format:

```
Rating: 4.5
Favorite track: Paranoid Android
Thoughts: Incredible album, every track is a journey.
```

**Rules:**

- The `Rating:` line is required. Value must be between 1.0 and 5.0.
- Text ratings must be in 0.5 increments (1.0, 1.5, 2.0, ... 5.0). The button
  modal is more lenient and rounds for you.
- `Favorite track:` and `Thoughts:` lines are optional.
- The bot reacts with a star on successful text ratings.

---

### Viewing Results

#### Week Overview

Run `/st-week overview` at any time to see the current week's status:
nominations count, current phase, and key dates.

You can also click the **"Refresh"** button on the pinned overview in the
nominations thread.

#### Ratings Summary

Run `/st-ratings summary` to see the aggregated ratings for the winning album:
average score, number of ratings, score distribution histogram, and review
excerpts.

#### Help

Run `/st-help` for a quick reference of all commands and the weekly flow.

---

## For Admins

Admin access requires either the **Manage Server** Discord permission or one of
the configured admin roles.

### Starting a New Week

```
/st-week start label:<week label>
```

| Option                 | Required | Description                                                   |
| ---------------------- | -------- | ------------------------------------------------------------- |
| `label`                | Yes      | Week label, e.g. `WEEK 003 [2025-11-24]`                      |
| `week_number`          | No       | Numeric week number (used for thread naming)                  |
| `nominations_close_at` | No       | When nominations close (ISO format, e.g. `2025-11-24T18:00Z`) |
| `poll_close_at`        | No       | When voting closes (ISO format)                               |
| `discussion_at`        | No       | When the listening session is scheduled (ISO format)          |

This creates a forum thread for nominations with a pinned overview message. If
you provide deadlines, the bot will post automatic reminders:

- 1 hour before nominations close.
- When nominations close.
- When voting closes.

### Opening the Poll

```
/st-poll open
```

Posts the nominee list and voting ballot button. Run this after the nomination
period is over. Optionally pass `week_id` to target a specific week.

### Closing the Poll and Announcing the Winner

```
/st-poll close
```

Tallies all votes, announces the winner, and posts the full results scoreboard.
Creates a winner thread in the forum. Optionally pass `week_id`.

### Opening Ratings

```
/st-ratings open
```

Posts the ratings prompt with a "Rate This Album" button and creates a ratings
thread. Can also be triggered by clicking the **"Open Ratings"** button on the
poll results. Optionally pass `week_id`.

### Typical Admin Workflow

1. `/st-week start label:WEEK 005 [2026-03-10] nominations_close_at:2026-03-12T20:00Z`
2. Wait for members to nominate.
3. `/st-poll open` -- when nominations close.
4. Wait for members to vote.
5. `/st-poll close` -- tallies votes and announces the winner.
6. `/st-ratings open` -- starts the ratings phase.
7. `/st-ratings summary` -- check how ratings are going.

---

## Command Reference

### Member Commands

| Command               | Description                                   |
| --------------------- | --------------------------------------------- |
| `/st-nominate`        | Open the nomination form for the current week |
| `/st-week overview`   | Show the current week's status and dates      |
| `/st-ratings summary` | Show ratings summary for the winning album    |
| `/st-help`            | Show the help panel with all commands         |
| `/ping`               | Check if the bot is online                    |

### Admin Commands

| Command            | Description                            |
| ------------------ | -------------------------------------- |
| `/st-week start`   | Create a new week and open nominations |
| `/st-poll open`    | Open voting for the current week       |
| `/st-poll close`   | Close voting and announce the winner   |
| `/st-ratings open` | Open ratings for the winning album     |

---

## Scoring and Tiebreakers

Votes are tallied using a ranked-choice system:

| Vote       | Points   |
| ---------- | -------- |
| 1st Choice | 2 points |
| 2nd Choice | 1 point  |

The nomination with the most total points wins. If there is a tie, the one with
the most 1st-place votes wins.

---

## Rating Rules

| Rule           | Details                                                 |
| -------------- | ------------------------------------------------------- |
| Scale          | 1.0 to 5.0                                              |
| Increments     | 0.5 steps (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0) |
| Modal behavior | Rounds to the nearest 0.5 automatically                 |
| Text behavior  | Must be an exact 0.5 increment or the bot rejects it    |

---

## Troubleshooting

| Problem                        | Solution                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------- |
| "No active weeks found"        | An admin needs to run `/st-week start` first                                 |
| Ballot expired                 | Click "Open Ballot" again (ballots expire after 30 minutes)                  |
| Text nomination not recognized | Make sure the first line is `Album -- Artist` and includes a `Why?:` line    |
| Text rating rejected           | Check that the `Rating:` value is between 1.0 and 5.0 in 0.5 increments      |
| Bot not responding             | Run `/ping` to check if it is online. If not, check the server logs.         |
| "You need admin permissions"   | You need the Manage Server permission or an admin role configured in the bot |
| "Missing nominations forum ID" | The `SIDETRACK_NOMINATIONS_FORUM_ID` environment variable is not set         |
