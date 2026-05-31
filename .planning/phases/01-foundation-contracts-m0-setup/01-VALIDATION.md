---
phase: 1
phase_name: Foundation & Contracts (M0 Setup)
audit_date: 2026-05-31
audit_type: goal-backward verification (issue-driven build — no PLAN/SUMMARY artifacts)
scope: merged code on `planning` branch
nyquist_compliant: false
verdict: substantively COMPLETE on merged code; 4 in-repo gaps logged before sign-off
---

# Phase 1 (M0) — Validation Audit

> This phase was built **issue-driven** (GitHub issues, not GSD plan/execute), so no
> `*-PLAN.md` / `*-SUMMARY.md` exist. This audit is a goal-backward verification of the
> ROADMAP success criteria + requirement IDs directly against the merged `planning` code.
> Coverage gate judged from `.github/workflows/backend.yml` (CI runs on Python 3.12 — local
> Python 3.9 cannot import the code and reports a false ~13%).

## Success Criteria

| # | Verdict | Notes |
|---|---------|-------|
| 1. Clean-clone `docker-compose up` → 3 Postgres + backend `/health`+`/docs`, frontend `next dev`, `pytest` green | **COVERED** | `docker-compose.yml` (app_db + institution_a:5433 + institution_b:5434 + backend); `api/health.py`; `next dev` script; 11 test files / 1750 lines. |
| 2. `model_validate()` all 6 R4B resources; `urn:uuid:`→`ResourceType/id` | **COVERED** (primitive) | `fhir/subset.py` (R4B imports + round-trip validate), `fhir/references.py:resolve_references` (non-mutating) + 8 tests. The `id_map` *builder* / ingest wiring is Phase-2 connector work (PR #58). |
| 3. Deterministic tagged-markdown flattener, every category w/ explicit status, never raw JSON | **COVERED** | `fhir/flatten.py` fixed category order, NKA-aware, `[ResourceType/id]` tags; `test_fhir_flatten.py` (17 tests). |
| 4. Provider ABC + Capability + FetchResult/Provenance/HealthStatus + registry + ConnectorError + coverage; `gen:api` → typed client | **PARTIAL** | Provider side fully covered (`providers/base.py`, `registry.py`, 16 tests). Client side: `openapi.json` is a **stale stub** (only `/health`+`/packet/{id}`, missing real `/patients/*` routes); typed client generated from it is behind the API. |
| 5. CI lint+typecheck+pytest+coverage gate on core; frontend lint+tsc+build; main protected (PR+≥1 review+CODEOWNERS) | **PARTIAL** | `backend.yml` (py3.12, ruff, black --check, pytest `--cov-fail-under=100` on fhir/providers/cache/knowledge/reasoning); `frontend.yml` (lint+tsc+test+build). Gaps: **no backend typecheck** (mypy/pyright absent — black≠typecheck); branch protection is a GitHub setting (not in-repo); CODEOWNERS routes **only `.planning/`**. |

## Requirements

| Req | Verdict | Notes |
|-----|---------|-------|
| FHIR-01 | COVERED | 6 builders + validate; loud-failure tests. |
| FHIR-02 | COVERED (primitive) | resolve_references + tests; ingest map-builder = Phase 2. |
| FHIR-03 | COVERED | tagged lines, never raw JSON. |
| FHIR-04 | COVERED | every category explicit status. |
| CONN-01 | COVERED | ABC + Capability + dataclasses + registry; 16 tests. |
| CONN-06 | COVERED | coverage dict / partial / warnings / ConnectorError. |
| SEC-02 | COVERED | `reasoning_view` strips PII, age-from-DOB, MRN-only, recursive, non-mutating; 13 tests (best-tested component). |
| SEC-03 | COVERED | `.env.example` placeholders; synthetic-only; `.env` gitignored. |
| API-08 | PARTIAL | OpenAPI 3.1 + slim DTOs + `separate_input_output_schemas=False` ✓; **`openapi.json` stale** vs live routes. |
| FE-07 | PARTIAL | `openapi-fetch` client ✓; **`openapi-react-query` not wired (unused dep)**; **no global bearer `.use()` middleware** (static header instead). |
| INFRA-01 | COVERED | runnable monorepo, boots, docker, tests. |
| INFRA-02 | PARTIAL | pipeline complete & blocks on red; **backend typecheck step missing**. |
| INFRA-04 | PARTIAL | CODEOWNERS exists but routes **only `.planning/`**; branch protection not in-repo. |
| OPS-01 | PARTIAL | config guard + `.env.example` + `test_config.py` ✓ (code done); **real-key provisioning (Hamza) is an external fact**, not confirmable in-repo. |

## Test Coverage Assessment

Two-tier bar met on backend correctness-critical code — CI `--cov-fail-under=100` on
`fhir/providers/cache/knowledge/reasoning` (py3.12). No genuine backend test gaps.
Frontend: `api-client.test.ts` checks only the typed surface; **no test for bearer
middleware / openapi-react-query** (because that wiring doesn't exist — see FE-07).

## Genuine Gaps vs Open-PR-Pending vs Out-of-Phase

**Genuine in-repo Phase-1 gaps (not in any open PR):**
1. **FE-07 incomplete** — wire `openapi-react-query` + a `.use()` global bearer middleware (criterion #4 + FE-07 require both). Most material spec miss.
2. **`openapi.json` stale** (API-08) — regenerate from the live app (`/patients/*`, `/connectors`, `/evidence/*` missing); `gen:api` currently emits a behind-the-API client.
3. **No backend typecheck in CI** (INFRA-02) — add mypy/pyright or formally accept the deviation (STATE.md acknowledges it).
4. **CODEOWNERS routes only `.planning/`** (INFRA-04) — add backend/frontend area ownership or accept.

**Open-PR-pending (correctly NOT on `planning`):** FHIR-02 ingest map (PR #58 / CONN-02, Phase 2); real Postgres cache (PR #55); openFDA/reasoning runtime (PR #56).

**Out-of-phase:** PDF connector (PR #59, Phase 4); Phase-2+ CONN/CACHE/KNOW/REASON/API runtime. `cache/`/`knowledge/`/`reasoning/` currently hold stand-ins/loaders sufficient for the 100% gate.

**External/ops (not a code gap):** OPS-01 real-key provisioning by Hamza.

## Bottom Line

Phase 1 / M0 is **substantively COMPLETE on merged code** — the fan-out spine (FHIR subset,
deterministic flattener, SEC-02 minimization, Provider contract, OpenAPI/typed-client path)
exists and is proven at the 100% gate. The STATE assumption that OPS-01 is the *lone*
outstanding item is only partially right: OPS-01's code is done, but **four in-repo gaps**
(FE-07 partial, stale `openapi.json`, no backend typecheck, `.planning`-only CODEOWNERS)
should be fixed-or-accepted before marking criteria #4/#5 fully green.

**Recommendation:** M0 is complete-enough to unblock parallel Phase-2 work. Run the standing
Phase-Boundary Review Gate (code-review → verify-work → secure-phase → add-tests) over the
above gaps before formally advancing to Phase 2.

## Manual-Only / Cannot-Verify-In-Repo

- Branch protection (PR + ≥1 review + required green checks) — GitHub server-side setting.
- OPS-01 real Gemini/openFDA key provisioning — local `.env` (gitignored), owner Hamza.
- "pytest green" — must be run on Python 3.12 (CI proves it; not runnable on local 3.9).
