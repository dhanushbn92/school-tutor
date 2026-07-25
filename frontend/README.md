# School Tutor — Frontend

React + TypeScript SPA for teachers, principals, and administrators.
Consumes the FastAPI backend at the repository root.

## Stack

- **Vite + React 19 + TypeScript** — build, HMR, typechecking
- **Tailwind CSS v4 + shadcn/ui-style components** (hand-built on Radix primitives) — design system
- **TanStack Query** — server state (caching, background refetch, mutation invalidation)
- **React Router v6** — client routing
- **Recharts** — line / heatmap / bar charts
- **react-hook-form + zod** — form validation
- **sonner** — toast notifications
- **lucide-react** — icon set

## Running locally

Two terminals, from the repo root.

### Terminal 1 — API

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

API serves at `http://127.0.0.1:8000`. Swagger docs at `/docs`.

### Terminal 2 — Frontend

```powershell
cd frontend
npm install    # first run only
npm run dev
```

SPA serves at `http://localhost:5173`. Vite proxies anything the app requests under `/api/*` to FastAPI on :8000 — no CORS fiddling while developing.

Sign in with any user from the demo seed:

| Role    | Email                          | Password     |
|---------|--------------------------------|--------------|
| Admin   | `admin@anaadi.demo`            | `admin123`   |
| Teacher | `priya.sharma@anaadi.demo`     | `teacher123` |
| Student | `student01@anaadi.demo` (…10)  | `student123` |

## Source layout

```
frontend/
├── src/
│   ├── App.tsx                     — routing + providers
│   ├── main.tsx                    — React bootstrap
│   ├── index.css                   — Tailwind import + design tokens
│   ├── lib/
│   │   ├── api.ts                  — axios instance, JWT attach, 401 handler
│   │   ├── auth.tsx                — <AuthProvider> + useAuth()
│   │   ├── queries.ts              — TanStack Query hooks (one per API)
│   │   ├── types.ts                — TS mirrors of Pydantic schemas
│   │   └── utils.ts                — cn(), date/number formatters
│   ├── components/
│   │   ├── ui/                     — Button, Card, Input, Label, Select, Badge, Skeleton, Empty
│   │   ├── layout/                 — Shell (sidebar + topbar), PageHeader, ProtectedRoute
│   │   ├── MasteryHeatmap.tsx      — chapter × outcome colour grid
│   │   └── StatCard.tsx            — dashboard stat tile
│   └── pages/
│       ├── Login.tsx
│       ├── Dashboard.tsx           — role-aware summary
│       ├── Sections.tsx            — list of classes I own
│       ├── SectionDetail.tsx       — gradebook + class-mastery heatmap + weakest outcomes
│       ├── StudentDetail.tsx       — per-student heatmap + trend line + intervention-note form
│       ├── Assessments.tsx         — list view
│       ├── AssessmentDetail.tsx    — questions + submissions
│       ├── QuestionBank.tsx        — filter by status, approve/reject/restore
│       ├── ContentLibrary.tsx      — grid of generated artifacts, filter by type
│       ├── Generate.tsx            — pick class/subject/chapter/type → submit → poll status
│       └── Curriculum.tsx          — chapters list + outcomes + text preview
```

## Data-fetching pattern

All API calls go through `src/lib/queries.ts`, which wraps axios in TanStack Query hooks:

```tsx
const { data, isLoading } = useMyAssessments();
```

- `staleTime: 30s` by default
- No refetch on window focus (quiet UX)
- Auth errors (401) clear the JWT and redirect to `/login`
- One query key per response shape so invalidation is surgical

## Build

```powershell
cd frontend
npm run build
```

Output lands in `frontend/dist/`. To serve the build from FastAPI in production, mount `StaticFiles(directory="frontend/dist", html=True)` on the app (not wired yet — MVP is dev-only).

## Known gaps (post-MVP)

- **Inline question edit** — bank supports approve/reject but no edit form yet. API already supports `PATCH /questions/{id}`.
- **Student self-serve take-assessment flow** — route exists, UI not yet.
- **Admin school-management CRUD** (create sections, enroll students) — admins use the backend seed script for MVP.
- **Long-generation status** polls every 2s; swap to SSE or WebSocket in production.
- **Code-splitting** — bundle is 858 KB / 260 KB gzipped. Lazy-load per route when this matters.
- **Dark mode** — design tokens exist; no toggle wired.
