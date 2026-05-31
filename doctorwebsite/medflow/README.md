# MedFlow — Umraa clinician demo

Next.js app: synthetic clinical UI for demos and design review. **No real PHI** — mock users and data only.

## Prerequisites

- Node.js **20+**
- npm **10+**

## Setup

From the **repository root**:

```bash
cd doctorwebsite/medflow
npm ci
cp .env.example .env.local
```

Edit `.env.local` if needed (`AUTH_SECRET` can be any non-empty string for local dev).

## Run

```bash
npm run dev
```

Open **http://localhost:3001** (dev server uses port **3001**).

For smoother demos (faster first paint per route):

```bash
npm run build && npm run start
```

## Demo sign-in (mock)

| Role | Email | Password |
|------|-------|----------|
| Clinician | `dr.wu@umraa.ca` | `password123` |
| Clinician | `dr.chen@umraa.ca` | `password123` |
| Patient | `patient@umraa.ca` | `password123` |
| Patient | `member@umraa.ca` | `password123` |

Clinician entry: `/login/clinician`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_SECRET` | Yes | NextAuth signing secret |
| `NEXTAUTH_URL` | Yes | App URL, e.g. `http://localhost:3001` |
| `AUTH_TRUST_HOST` | Yes | Set `true` for local and Vercel |

Copy from [`.env.example`](.env.example). Do not commit `.env.local`.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Development server (port 3001) |
| `npm run build` | Production build |
| `npm run start` | Production server (port 3001) |
| `npm run lint` | ESLint |

## Layout

- `app/` — App Router pages
- `components/` — UI components
- `lib/mock-data/` — Synthetic patient/clinical data
- `auth.ts` — NextAuth credentials provider (mock users)

## More detail

- [`handoff.md`](handoff.md) — Routes, design tokens, mock-data helpers
- [`AGENTS.md`](AGENTS.md) — Next.js 16 notes for coding agents

## Deploy

Deploy as a standard **Next.js** app (e.g. Vercel). Set the same env vars as in `.env.example` in the host dashboard.
