# Doctor website (Umraa)

All clinician-facing website work for Umraa lives under this folder. The main app is **MedFlow**, a Next.js EMR-style demo with synthetic data.

## Projects

| Path | Description |
|------|-------------|
| [`medflow/`](medflow/) | Next.js 16 clinician & patient demo UI — **start here** |
| [`design_handoff_medflow_nav/`](design_handoff_medflow_nav/) | Wireframe / nav handoff assets |

## Quick start (MedFlow)

```bash
cd doctorwebsite/medflow
npm ci
cp .env.example .env.local
npm run dev
```

Open **http://localhost:3001**. See [`medflow/README.md`](medflow/README.md) for demo logins, env vars, and production build.

## Not in this folder

Backend API, FHIR connectors, and the provider `frontend/` app remain in the repo root (`backend/`, `frontend/`). This directory is only the standalone website demo.
