# Royal Square Frontend

React + TypeScript + Vite frontend for the Royal Square client and adviser workspaces.

## Run

```sh
npm install
npm run dev
```

`npm run build` checks TypeScript and builds the application. `npm run test:e2e` runs the browser workflow tests (Playwright Chromium must be installed).

## Demo behaviour

Switch between Client and Adviser in the header. The client account is Thando Mokoena; all records are synthetic. Claims, goals, reminders, requests and email drafts persist in localStorage. Attachment names are retained, not file contents. The accident checklist persists separately.

The document assistant uses explicitly labelled sample guides and deterministic responses with viewable page references. It does not call an LLM or search production documents. The inbox contains sample messages and only saves drafts. No email is sent. Role switching is a demo control, not authentication.

## Backend integration

`src/data.ts` defines shared record types, seed data and the local repository. Replace this storage boundary with API queries and mutations when FastAPI is available. TanStack Query is configured at the root. Replace demo role selection with authenticated role claims and enforce ownership on the server. Policy and client records currently use fixture arrays. File storage, reminder delivery, genuine document retrieval, Gmail OAuth and sending remain backend work.

Deploy the generated `dist` directory with SPA fallback to `index.html`. Currency is ZAR. The meeting-room photo uses Unsplash; fonts use Google Fonts with local system fallbacks.
