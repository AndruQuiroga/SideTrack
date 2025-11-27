# Sidetrack Web (Frontend)

This is a **barebones but polished** frontend prototype for the Sidetrack reboot.

- Built with **Next.js (App Router)** + **TypeScript**.
- Styled with **Tailwind CSS** and a dark, gradient-heavy aesthetic.
- Uses **static sample data** to sketch:
  - Home overview.
  - Club archive.
  - Week detail gallery.
  - A sample listener profile.

It does **not** talk to a real API yet – it is meant as a starting point for wiring in the Sidetrack backend.

## Getting started

```bash
pnpm install
pnpm dev
```

Then open http://localhost:3000.

## Key routes

- `/` – Overview: latest Album of the Week hero + explainer.
- `/club` – Grid of recent weeks (album cards).
- `/club/week-003` – Example week detail page.
- `/u/dreski` – Example listener profile.
- `/discover` – Placeholder for future social / compatibility views.

## Next steps

- Replace `lib/sample-data.ts` with real API calls.
- Wire in authentication and account linking.
- Add charts for taste profiles and compatibility.
- Align with the backend contracts defined in the Sidetrack `agents/*.md` docs.
