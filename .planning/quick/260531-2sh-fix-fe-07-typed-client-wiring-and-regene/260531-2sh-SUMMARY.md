---
quick_id: 260531-2sh
description: Fix FE-07 typed-client wiring and regenerate stale openapi.json (Phase-1/M0 contract gaps)
date: 2026-05-31
status: complete
branch: feat/fe07-openapi-contract
commits:
  - 3c1341c feat(frontend): wire FE-07 bearer middleware and openapi-react-query $api
  - 4ce80e7 chore(frontend): regenerate openapi.json from live API and cover live routes
---

# Quick Task 260531-2sh — Summary

Closed the two genuine in-repo Phase-1/M0 contract gaps surfaced by the
`01-VALIDATION.md` audit (FE-07 partial; API-08 stale `openapi.json`).

## Task 1 — FE-07 typed-client wiring (commit 3c1341c)

`frontend/lib/api/client.ts`:
- Replaced the static, construction-time `Authorization` header with a
  **per-request bearer `.use()` middleware** (`bearerMiddleware`): `onRequest`
  reads `process.env.NEXT_PUBLIC_API_TOKEN` on every request and sets
  `Authorization: Bearer <token>` only when a token is present.
- Wired **`openapi-react-query`** (previously an unused dependency):
  `createQueryClient(apiClient)` exported as `$api` (default export aliased to
  `createQueryClient` to avoid the `createClient` name collision with
  `openapi-fetch`).
- `index.ts` now re-exports both `apiClient` and `$api`.

## Task 2 — regenerate stale openapi.json (commit 4ce80e7)

- `frontend/openapi.json` was a Stage-B stub (only `/health` + `/packet/{patient_id}`).
  Regenerated from the **live FastAPI app** by importing `backend.app.main:create_app`
  under a throwaway **Python 3.12** venv (local `python3` is 3.9 and cannot import the
  backend) and dumping `create_app().openapi()`.
- Contract now exposes the real routes: `/health`, `/patients`,
  `/patients/{patient_id}/packet`, `/patients/{patient_id}/resource/{resource_type}/{resource_id}`,
  `/patients/{patient_id}/refresh`, `/connectors`, `/evidence/{evidence_id}` (OpenAPI 3.1.0).
- `lib/api/generated.ts` regenerated via `npm run gen:api`.
- `tests/api-client.test.ts` extended to assert the regenerated path surface
  (patients/packet/citation/refresh/connectors/evidence/health) plus the bearer
  middleware inject/omit behaviour and `$api.useQuery` wiring.

## Verification (frontend/)

| Gate | Result |
|------|--------|
| `npm run lint` (eslint) | PASS (exit 0) |
| `npm run typecheck` (tsc --noEmit) | PASS (exit 0) |
| `npm test` (vitest) | PASS — 7/7 tests |

Confirmed `openapi.json` contains `/patients`, `/connectors`, `/evidence/...` (no
longer the stub). No backend code touched. No AI-trace watermarks in commits/code.

## Notes / follow-ups

- The throwaway py3.12 venv lived under `/tmp` and was not committed.
- Remaining Phase-1 audit items NOT in this task (minor, by design): no backend
  typecheck step in CI (INFRA-02) and CODEOWNERS routes only `.planning/` (INFRA-04)
  — fix-or-accept during the phase-boundary gate.
- Next: push branch, open PR into `planning` (protected: PR + 1 review).
