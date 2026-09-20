# Royal Square Frontend

React 19 + TypeScript + Vite. This branch retains its navy/ruby workspace, compact sidebar and client dashboard design, with the feature modules from the locally available `origin/main` snapshot `394c4e7`.

## Run

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Set `VITE_API_URL` to your backend origin (without `/api/v1`) and configure the public Supabase URL and anon key in `.env.local` for authenticated use. Never put service keys or access tokens in frontend source. Empty `VITE_API_URL` or `mock` enables explicitly synthetic in-memory demo data and the client/adviser role selector. Demo changes reset on reload; the previous localStorage prototype is no longer the active data source.

## Features

- Authenticated client, adviser and owner routes with role guards and session refresh.
- Client policies, goals, reminders, profile, claim registration/tracking and configurable requests.
- Adviser client records, claims pipeline, document assistant, email drafts and opportunity workflows.
- Owner business health and drilldowns; identity vault, advice/consent records, compliance packs, audit history, privacy controls and notifications.

The frontend uses the API contract on `origin/main` at `394c4e7`. This branch's backend and `docs/api.md` are older and have not been changed by this frontend integration. In particular, owner/radar, workflow/notifications, identity, and compliance/audit features require the corresponding backend updates from main. The imported offline mock covers the earlier client/adviser APIs; it does not implement the newer endpoints. Errors from unsupported endpoints are displayed rather than represented as successful operations. Use a matching synthetic backend to exercise those features end to end.

## Checks

```sh
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests start their own Vite server in mock mode and cover authentication guards, workspace navigation, adviser search, reminder updates and responsive layouts. They do not verify a live Supabase session or the newer backend endpoints.

Deploy `dist` with SPA fallback to `index.html`. The existing logo assets, fonts and meeting-room image are retained. No emails are sent by the frontend; drafts require human review.
