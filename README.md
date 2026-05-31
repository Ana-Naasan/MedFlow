# Umraa

Stage B scaffold for the polypharmacy decision packet. The repo is set up so the platform pair can branch immediately while the reasoning and connector work lands behind stable contracts.

## What is here

- `backend/` FastAPI scaffold with `/health`, `/docs`, contract DTOs, provider base types, and pytest coverage for the smoke path.
- `frontend/` Next.js + TypeScript scaffold with TanStack Query, a typed OpenAPI client stub, and smoke tests.
- `docker-compose.yml` three Postgres services for the app database plus `institution_a` and `institution_b`.
- `.planning/` requirement and roadmap traceability for the PRD.

## Quick start

1. Copy `.env.example` to `.env` and fill in the local values.
2. Set `GOOGLE_GENAI_API_KEY=PLACEHOLDER`, `OPENFDA_API_KEY=PLACEHOLDER`, and `DEV_TOKEN=PLACEHOLDER` in `.env` before wiring real values.
3. Verify the config-load test passes before you rely on the AI or openFDA lookups.
4. Install backend dependencies with `make backend-install`.
5. Install frontend dependencies with `make frontend-install`.
6. Run `make test` and `make lint`.
7. Start the backend with `cd backend && uvicorn app.main:app --reload`.
8. Start the frontend with `cd frontend && npm run dev`.
9. Start the database layer with `docker compose up`.

## Environment

The reasoning and drug-data lookups require `GOOGLE_GENAI_API_KEY`, `OPENFDA_API_KEY`, and `DEV_TOKEN`. Keep real values only in local `.env`; `.env.example` contains `PLACEHOLDER` values so nobody checks secrets into the repo.

## Branching and review

Work in short-lived feature branches off `main`. Open a PR for every change set, keep the review focused on the correctness-critical path first, and use the two-tier rigor bar from `CONTRIBUTING.md` when deciding how hard to test and review a change.