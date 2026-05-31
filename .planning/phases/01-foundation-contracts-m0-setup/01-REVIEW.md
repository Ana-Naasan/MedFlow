---
phase: 1
phase_name: Foundation & Contracts (M0 Setup)
review_date: 2026-05-31
review_type: phase-boundary review gate (report-only, multi-agent)
scope: merged code on `planning` @ 1bc0dad
method: 4 dimensions (code-review · criteria-verification · security · test-adequacy), Opus, read-only; high-severity + security findings adversarially re-verified against source
verdict: substantively COMPLETE — no merge-blockers; 3 verified HIGH items (1 fixed here, 2 deferred to in-flight cache/auth work)
companion_pr: "#69 — fixes SEC-02 + HL7v2 + contract tests (this branch)"
---

# Phase 1 (M0) — Boundary Review Gate

> Companion to `01-VALIDATION.md` (the earlier goal-backward audit). This is the
> standing phase-boundary gate (code-review → verify-work → secure-phase →
> add-tests), run report-only over the merged `planning` code. Findings were
> produced by 4 independent Opus reviewers; every HIGH-severity and security
> finding was then adversarially re-verified against the actual source before
> inclusion. The fixes for the isolated findings ship in the same PR (#69);
> findings on the in-flight cache/auth surface are deferred (see §Deferred).

## Tooling baseline (Python 3.12 / CI runtime)

| Check | Result |
|-------|--------|
| backend `ruff` | ✅ clean |
| backend `black --check` | ✅ clean |
| backend `pytest` | ✅ 247 → **255** passed (this PR adds 8) |
| core coverage gate (`fhir/providers/cache/knowledge/reasoning`) | ✅ **100.00%** (`--cov-fail-under=100`) |
| frontend `eslint` / `tsc --noEmit` / `vitest` | ✅ clean / clean / 7 passed |

The automated gate is green; the findings below are what linters and line-coverage do not catch.

## Success criteria

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Clean clone → docker-compose 3× Postgres + backend `/health`+`/docs`, frontend `next dev`, `pytest` green | **TRUE** (containers + routes present; "pytest green" proven on CI 3.12) |
| 2 | `model_validate()` all 6 R4B resources; `urn:uuid:`→`ResourceType/id` | **TRUE** (subset builders + `resolve_references`, single-pass) |
| 3 | Deterministic tagged flattener, every category explicit status, never raw JSON | **TRUE** (determinism now pinned by test in this PR) |
| 4 | Provider ABC + dataclasses + registry + `ConnectorError` + coverage; `gen:api` → typed client | **PARTIAL** — Provider side complete; OpenAPI exposes no DTO schemas (routes lack `response_model`) so the typed client is untyped on core payloads (API-08) |
| 5 | CI lint + **typecheck** + pytest + coverage gate; frontend lint+tsc+build; `main` protected + CODEOWNERS | **PARTIAL** — no backend typecheck step (INFRA-02); CODEOWNERS routes only `.planning/` (INFRA-04); branch protection is server-side (manual-verify) |

## Requirement verdicts (M0)

| Req | Verdict | Note |
|-----|---------|------|
| FHIR-01/03/04 | TRUE | builders+validate; flattener tagged/explicit/never-raw |
| FHIR-02 | TRUE | `resolve_references` non-mutating, single-pass (now tested) |
| CONN-01/06 | TRUE | ABC + Capability + dataclasses + registry + coverage/partial/ConnectorError |
| SEC-02 | **HARDENED (this PR)** | was a deny-list missing Synthea identity fields → now fail-closed allow-list |
| SEC-03 | TRUE | synthetic-only; `.env` gitignored; `.env.example` placeholders only |
| API-08 | PARTIAL | `separate_input_output_schemas=False` ✓ but routes lack `response_model` → no DTO schemas emitted |
| FE-07 | TRUE (re-verified post #61/#64) | `openapi-fetch` + `$api` (openapi-react-query) + bearer wiring present |
| INFRA-01 | TRUE | runnable monorepo / docker / boots |
| INFRA-02 | PARTIAL | lint+pytest+coverage gate present; **no typecheck step** |
| INFRA-04 | PARTIAL | CODEOWNERS `.planning/`-only; branch protection server-side |
| OPS-01 | PARTIAL | config guard + `.env.example` done (code); real keys external (Hamza / GCP deploy) |

## Findings

Severity shown is the **adversarially-verified** severity. `FIXED` = addressed in PR #69; `DEFERRED` = intentionally out of this PR (see §Deferred).

### 🔴 HIGH

1. **SEC-02 PHI minimization deny-list has holes** — `fhir/subset.py` `reasoning_view` — **FIXED**
   `_PII_KEYS` (deny-list) missed `text`, `photo`, `communication`, `maritalStatus`,
   `generalPractitioner`, `managingOrganization`, and the Synthea identity `extension`
   array (race / ethnicity / mother's-maiden-name / birthplace) — any could carry PHI
   into the reasoning context. Compounded by `reasoning_view` being dead code (no live
   barrier yet — acceptable as reasoning is Phase 2).
   → Replaced with a **fail-closed allow-list** for Patient (keep only
   `resourceType`/`id`/`gender`/`ageYears`/MRN identifier); unknown/future fields drop.

2. **Audit-on-read (CACHE-03) bypassed at the API edge** — `api/packet.py` — **DEFERRED**
   `repo.get_resource`/`repo.get_evidence_card` write an `AuditEvent` on every read, but
   the citation/evidence handlers call the un-audited static-store functions, and
   `POST /refresh` calls `upsert_resource` with no audit row. The guarantee holds in the
   repo, not at the HTTP edge. This is the owed follow-up already logged in `STATE.md`
   ("wire get_or_refresh + X-Cache into api/packet.py off the store.py stand-in").
   *(Reviewer mislabeled CACHE-04; it is CACHE-03.)*

3. **Auth failure paths untested** — `api/auth.py` + `test_packet.py` — **DEFERRED**
   No test covers 401-missing-token, 401-invalid-token, or 500-missing-`DEV_TOKEN`.
   Same `auth.py`/`packet.py` surface as #2; deferred to coordinate.

### 🟠 MEDIUM

| Finding | Area | Status |
|---------|------|--------|
| No-PID HL7v2 message fabricated `Patient/unknown` (guard was dead — `hl7apy` auto-materialises an empty PID) | `providers/hl7v2.py` | **FIXED** → raises `ConnectorDataError` on empty PID-3 |
| Flattener determinism / intra-category order never asserted | `fhir/flatten.py` | **FIXED** (test) |
| OpenAPI exposes no `DecisionPacket`/`Hypothesis`/`Citation` schemas (routes lack `response_model`) | API-08 | DEFERRED (touches `packet.py`) |
| No backend typecheck (mypy/pyright) in CI | INFRA-02 | DEFERRED (CI config) |
| CODEOWNERS routes only `.planning/` | INFRA-04 | DEFERRED (infra) |
| Once-only-refresh unverified under real concurrency (SQLite grants the advisory lock optimistically) | `cache/repo.py` | DEFERRED (needs `live` Postgres test) |
| Default DB is in-memory SQLite (data lost on restart, no cross-process integrity) | `database.py`/`main.py` | DEFERRED (infra decision: fail-fast if `DATABASE_URL` unset) |
| Citation/evidence 404 paths untested; packet returns 200 for a non-existent patient; citation closed-loop integrity only half-asserted | `api/packet.py` | DEFERRED (packet surface) |

### 🟡 LOW

| Finding | Area | Status |
|---------|------|--------|
| Reference resolver single-pass / cyclic behavior not pinned | `fhir/references.py` | **FIXED** (test) |
| Year-only / `YYYY-MM` birthDate loses `ageYears` | `fhir/subset.py` `_compute_age_years` | noted (full-ISO only) |
| Token-bucket benign read-modify-write race in slow path | `knowledge/openfda.py` | noted (best-effort; 200<240/min) |
| `reasoning_view` is dead code — no live PHI barrier yet | `fhir/subset.py` / `reasoning/` | noted (enforce at reasoning choke point in Phase 2) |
| Dev bearer token compared with non-constant-time `!=` | `api/auth.py` | DEFERRED (auth surface; `hmac.compare_digest`) |
| No enforced "citations must resolve" invariant before serving | `cache/store.py` | DEFERRED (enforce when reasoning lands) |
| `openfda._first_text` stringifies a mid-path dict | `knowledge/openfda.py` | noted (brittle test assertion) |

## Confirmed correct / intentional (no action)

- FHIR builders re-validate via round-trip; `resolve_references` non-mutating & single-pass.
- openFDA query escaping closes the Lucene-injection hole; **no SSRF / unsafe deserialization**.
- Cache repo: tz-coercion of naive SQLite datetimes, audit-on-every-read at the repo layer, no-duplicate upserts.
- `.env.example` holds dev placeholders only — **no real secrets committed**; `.env` gitignored.
- Unmatched `urn:uuid:` references left intact by design (detectable downstream); untagged flattener lines are section headers (intentional).
- No data-corruption, no mutable-default aliasing, no incorrect `await`, no resource leaks in the reviewed core.

## Fixed in PR #69 (this branch)

- **SEC-02** fail-closed allow-list (`fhir/subset.py`) + 3 hardening tests (Synthea identity fields dropped; fail-closed on unknown fields; contained-Patient minimised).
- **HL7v2** no-PID → `ConnectorDataError` (`providers/hl7v2.py`) + 2 tests (parser + provider paths).
- **Flattener determinism** test (identical output across calls; input order preserved).
- **Reference resolver single-pass** test.

Gated core stays at 100%; +8 tests; ruff/black clean.

## Deferred (intentionally NOT in this PR)

To avoid colliding with the in-flight cache/auth wiring and infra config, these are left for the owning work:

1. **Audit-on-read at the API edge** + **auth-failure tests** (HIGH #2/#3) — the `api/packet.py` / `cache/store.py` / `auth.py` surface, which is the `STATE.md` owed cache-wiring follow-up.
2. **API-08** `response_model` annotations (+ regen typed client) — touches `packet.py`.
3. **Backend typecheck step** in `backend.yml` (INFRA-02) and **CODEOWNERS area routing** (INFRA-04) — repo/infra config.
4. **Live Postgres concurrency test** for once-only refresh (CACHE-03).
5. **Fail-fast on missing `DATABASE_URL`** outside tests.
6. Low nits: constant-time token compare, partial-date `ageYears`, token-bucket lock, `_first_text` mid-path dict.

## Manual-only / cannot verify in-repo

- Branch protection (PR + ≥1 review + required green checks) — GitHub server-side setting.
- OPS-01 real Gemini/openFDA key provisioning — external (Hamza / GCP deploy).
- "pytest green" — must run on Python 3.12 (local 3.9 cannot import `UTC`/`slots`).
