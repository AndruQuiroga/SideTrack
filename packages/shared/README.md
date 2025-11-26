# Shared Package

This package exposes TypeScript contracts and a thin API client shared by the Discord bot, web app, and other services.

## Contents

- Typed interfaces mirroring the FastAPI schemas for club weeks, nominations, votes, ratings, users, and linked accounts.
- A configurable Axios-based `SidetrackApiClient` with helpers for weeks, ratings, nominations, votes, and account linking.
- Error utilities (`ApiError`, retryable status helpers) to standardize client-side handling.

## Usage

```ts
import { SidetrackApiClient, ProviderType, WeekCreate } from '@sidetrack/shared';

const client = new SidetrackApiClient({
  baseUrl: process.env.API_BASE_URL ?? 'http://localhost:8000',
  authToken: process.env.API_TOKEN,
});

const newWeek: WeekCreate = {
  label: 'Week 42 — Cosmic Synthwave',
  week_number: 42,
};

async function bootstrapWeek() {
  const created = await client.createWeek(newWeek);
  const summary = await client.getWeekRatingSummary(created.id, { include_histogram: true });
  console.log({ created, summary });
}
```
