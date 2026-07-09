# ProspectusAI Frontend

A React + Vite + TypeScript frontend for the ProspectusAI RAG chatbot: a public
chat interface plus a (mock-authenticated) admin dashboard.

## Stack

- React 18 + TypeScript
- Vite
- React Router v6
- Tailwind CSS
- No Next.js, no database, no Docker

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # already included with a sensible default
npm run dev
```

The app runs at `http://localhost:5173` and expects the backend at
`http://127.0.0.1:8000` (configurable via `VITE_API_BASE_URL` in `.env`).

## Build

```bash
npm run build
```

This type-checks with `tsc -b` and then produces a production build in `dist/`.

> Note: this project was authored in a sandboxed environment without npm
> registry access, so `npm install` / `npm run build` could not be executed
> here to confirm a clean compile. All files were written and manually
> reviewed for type-correctness against a standard `vite react-ts` +
> `react-router-dom` + `tailwindcss` setup, but please run `npm install &&
> npm run build` yourself as the first step and report back any TypeScript
> errors — happy to fix immediately.

## Routes

| Route | Description |
|---|---|
| `/` | Redirects to `/chat` |
| `/chat` | Public chatbot — no login required |
| `/admin/login` | Admin login (mock auth, dev only) |
| `/admin` | Protected admin dashboard |

## Chat

Calls the real backend:

- `POST /api/v1/chat` — `{ question }` → `{ answer, status, sources, page_references }`

Behavior:
- Duplicate sends are blocked while a request is in flight.
- If `status` is `needs_page_review`, a prominent amber card is shown per
  `page_references` entry with the page number, reason, and a **"View page
  N"** button that opens `page_url` (prefixed with `VITE_API_BASE_URL`) in a
  new tab. Wording deliberately avoids asserting the page contains the
  answer — it frames it as "worth checking yourself".
- Sources are shown in a collapsible list (document, page, heading, score).
- Network / non-2xx errors show an inline error bubble instead of crashing.

## Admin

### Mock auth (temporary, development only)

The real admin backend (`POST /api/v1/admin/login`) is **not built yet**, so
`src/services/adminService.ts` includes a clearly-labeled, isolated mock:

- Username: `admin`
- Password: `prospectus-dev-only`

This is **not a real credential** — it's a local-only check against
constants in the frontend, purely so the dashboard can be built/demoed. The
session is written to `sessionStorage` (cleared on tab close) and never sent
over the network. The login page also displays this mock-credential notice
to whoever is running the app.

Swap it out by editing `AuthContext.tsx` to call `loginAdmin(...)` (already
implemented in `adminService.ts`, wired to the real endpoint) instead of
`mockLogin(...)`, once the backend exists.

### Real (planned) endpoints

Frontend functions already exist for these and call gracefully when the
route 404s or the server is unreachable, returning a `BackendCallResult` so
the UI can render a **"This backend feature is not connected yet"** notice
instead of breaking:

- `POST /api/v1/admin/login`
- `POST /api/v1/admin/upload`
- `GET /api/v1/admin/documents`
- `GET /api/v1/admin/processing-status/{document_id}`

### Dashboard contents

- Active prospectus card
- PDF upload area (drag & drop or click to browse)
- Processing pipeline: Uploaded → Parsing → Extracting tables → Building
  chunks → Building graph → Indexing → Ready
- Processing summary: total / processed / failed / quarantined pages
  (placeholders, clearly marked as not connected until the backend exists)

No fake real-world numbers are hardcoded — placeholders show `—` until a
real document/summary is available from the backend.

## Design

Bright, student-focused, trustworthy: blue/purple/cyan gradient accents,
soft colorful page background, rounded 2xl cards, soft shadows. Colors are
defined as Tailwind theme tokens in `tailwind.config.js` (`brand.blue`,
`brand.purple`, `brand.teal`, `brand.cyan`) so they're easy to retune in one
place.

## Project layout

```
src/
  components/
    chat/        ChatWindow, ChatInput, MessageBubble, SourcesList,
                 PageReviewCard, ExampleChips
    admin/       ActiveProspectusCard, UploadArea, ProcessingStages,
                 SummaryCards
    layout/      Navbar, ProtectedRoute
  context/       AuthContext (mock admin session)
  pages/         ChatPage, AdminLoginPage, AdminDashboardPage, NotFoundPage
  services/      api.ts (shared fetch wrapper), chatService.ts,
                 adminService.ts
  types/         chat.ts, admin.ts
```
