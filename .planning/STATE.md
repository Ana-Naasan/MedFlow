# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Last activity: 2026-05-31 — cleared the PR queue with full code+test review → approval → admin squash-merge → close, for both PR #47 (#21 drug-knowledge seeds) and PR #48 (#5 FHIR subset/refs/minimize). Took Copilot's bot reviews into account on both (details under Blockers). Queue empty; `planning` synced; working tree clean.

Progress (Phase 1 / M0): [██████▌░░░] ~65%

**Branch model:** `planning` = protected dev branch (PR + 1 review; teammates fully gated); `main` = submission branch. `.planning/` is owned by **@B2707 only** (CODEOWNERS + code-owner review; owner pushes `.planning` updates directly).

### Open PRs / In Review

_None — queue clear._

### Done (on `planning`, green)

- #1 spike — all 6 FHIR R4B resources import + `model_validate` (8 tests)
- #2 scaffold — runnable monorepo (backend `/health`+`/docs`, frontend, docker-compose 3× Postgres)
- #3 Provider ABC — registry + FetchResult/Provenance/HealthStatus + ConnectorError + coverage contract (11 tests). The fan-out unblocker.
- #4 DTO/OpenAPI contract — Citation/Hypothesis/DecisionPacket DTOs + `/packet` stub + regenerated typed client (PR #45). Frontend can now build against the typed client.
- #7 CI — backend + frontend pipelines, coverage gate scaffolded (relaxed to 0 until core code lands)
- #9 (partial) — required-secret config guard + `.env` placeholders merged (PR #46). #9 stays OPEN until real Gemini/openFDA keys are provisioned in local `.env`.
- #21 seed data — DDInter (10k interaction pairs), ACB scale, AGS 2023 Beers, Synthea sample FHIR bundle + text-layer clinical PDF vendored to `backend/app/seeds/` with provenance (SOURCES.md) + typed loaders + 26 tests (PR #47). Synthetic data only.
- #5 FHIR subset — `fhir/subset.py` (6 validated R4B builders via `fhir.resources.R4B.*` killing the R5-default gotcha + `reasoning_view` SEC-02 minimization: strips name/address/telecom/contact, drops birthDate→`ageYears`, keeps MRN-only identifiers, recursive incl. contained, non-mutating) + `fhir/references.py` (`urn:uuid:`→`ResourceType/id`, non-mutating) + 26 tests (PR #48). Full suite green. Unblocks #6, #11. NOTE: deterministic flattener (FHIR-03/04) NOT in this PR — still outstanding for the citation-tagged reasoning context.

### Ready / unblocked now

- #6, #11 (Mohammad) — unblocked by #5 FHIR subset now merged
- Flattener (FHIR-03/04, deterministic citation-tagged context) — outstanding; scoped under #5's intent but not delivered in PR #48. Needs an owner/issue before Phase 2 reasoning.
- #12 cache (Bader), #23 Postgres connector (Bader+Hamza), #28 HL7v2 scaffold (Vivek), #33 observability (Bader)
- #20 RxNorm normalization, #22 interaction checking, #26 older-adult (Beers/ACB) lookups, #27 PDF connector demo — all unblocked by #21 seed data
- #9 provisioning (Hamza) — config guard merged; real keys go in local `.env` (`GOOGLE_GENAI_API_KEY`, `OPENFDA_API_KEY`, `DEV_TOKEN`) to unblock the reasoning runtime (#14, #15)

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: Provider `abc.ABC` + registry-dict factory built FIRST — the Provider contract + DTO/OpenAPI stub fan out to unblock all connectors AND the frontend (typed client) in parallel.
- [Phase 1]: FHIR R4 subset of exactly 6 resources via `fhir.resources.R4B.*` (R4B import avoids the R5-default gotcha); slim Pydantic DTOs, not raw FHIR (`separate_input_output_schemas=False`).
- [Phase 2]: Hour-6 vertical-slice gate (PRD §22) with explicit connector cut order HL7v2 → PDF → Postgres if not green by hour 6.
- [All]: Anti-hallucination is structural — deterministic post-generation verifier drops any unresolved citation before the UI. No vector DB anywhere.
- [All]: Two-tier quality bar — correctness-critical components (reasoning core, verifier, connector→FHIR mappers, cache refresh-on-read, citation resolution, knowledge joins) get full tests + coverage gate; polish/enrichment ship fast.

### Pending Todos

From Copilot bot reviews on the two merged PRs (all on already-merged code — fix-forward via small PR or follow-up issues to the owners):
- [#21 / Vivek] `seeds/acb.json` has a duplicate drug entry with a conflicting ACB score (Copilot: nortriptyline) — name/RxCUI lookup could return inconsistent burden. De-dupe.
- [#21 / Vivek] `seeds/SOURCES.md` lists warfarin as present in `sample_bundle.json`, but the bundle has no warfarin / RxCUI 11289 (only aspirin + prasugrel). The warfarin+aspirin planted interaction lives in the Beers rule + `sample_clinical.pdf`, NOT the FHIR bundle — so fix the provenance note (don't point interaction-demo work at a non-existent bundle med).
- [#21 / Vivek] `seeds/SOURCES.md` references a PDF-generator path that doesn't exist in the repo — provenance not reproducible. Commit the script or drop the path.
- [#5 / Mohammad] `fhir/references.py` signature is typed `dict[str, Any]` but the function intentionally passes through non-dict (`None`/`str`/`int`); docstrings were corrected to `Any` but the annotation wasn't. Cosmetic (ruff doesn't type-check), tidy when convenient.
- [#5 / Mohammad] `reasoning_view` docstring example hard-codes `ageYears = 36` (date-dependent; not run as a doctest). Swap for a stable assertion in the docstring.

### Blockers/Concerns

- [Phase 1 — CRITICAL PATH]: #3 Provider ABC, #4 DTO/OpenAPI, #5 FHIR subset, #21 seed data all MERGED ✓ — M0 fan-out complete: connectors, cache, frontend, knowledge, reasoning inputs all unblocked. Remaining Bader critical-path code: #12 cache (M1 §22 slice prerequisite), #23 Postgres connector, #17 API, #33 observability.
- [Phase 1 — GAP]: deterministic **flattener (FHIR-03/04)** not yet implemented — PR #48 delivered builders + minimization + ref-resolution but not the citation-tagged markdown flattener, a hard prerequisite for the Phase 2 reasoning core. Confirm/open the owning issue before M1.
- [Process]: `planning` is protected (PR + 1 review). Flow per PR = code review + test run → formal approve → admin squash-merge → close issue+PR. **Take the Copilot bot review into account every time** (it caught a valid SEC-02 gap on #48 — author fixed it pre-merge in commit `bdcc3948` — plus the #21 data nits now in Pending Todos). Watch for AI-trace watermarks: PR #44 had `Co-Authored-By: Claude`+`🤖`; PR #48 had per-commit `Co-authored-by: Copilot Autofix` trailers — all dropped by squash (verified clean on the squash commits). No Claude/AI references anywhere per project policy.
- [Process — git]: `gh pr merge --squash` mutates `origin` server-side; ALWAYS `git fetch && git reset --hard origin/planning` before the next local `.planning` doc-sync commit, or a stale-branch push reverts the merge (a stale STATE push was correctly rejected non-fast-forward this session; recovered).
- [Phase 2]: The hour-6 §22 gate is the survival floor — the MockFHIR → cache → flatten → reason → verified cited hypothesis → /packet → rendered clickable citation chain must be green before widening. Watch the clock; apply the cut order if at risk.
- [Phase 3]: RxNav→DDInter/Beers/ACB bridge is keyed by name/ingredient/ATC (not RxCUI) — a string/class match with miss risk (salts, synonyms, combos); needs the flagged fallback and manual verification for demo drugs.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-31
Stopped at: Phase 1 (M0) ~65%. Cleared the PR queue: PR #47 (#21 seeds, 26 tests) and PR #48 (#5 FHIR subset/refs/minimize, 26 tests + full suite green) both reviewed (code + tests + Copilot bot review) → approved → admin squash-merged → issues #21/#5 closed, branches deleted. Squash commits verified AI-trace-clean. Copilot's non-blocking findings captured in Pending Todos. Queue empty; `planning` synced; tree clean.
Resume file: None
Next: (1) decide handling of the Copilot Pending Todos (small fix-forward PR vs. follow-up issues to Vivek/Mohammad); (2) resolve the flattener gap (FHIR-03/04 owner/issue) before M1; (3) pick up Bader's unblocked critical-path code — #12 cache (M1 §22 prerequisite), #23 Postgres connector, #17 API, #33 observability. Review incoming PRs (code+test+Copilot before merge). Watch the hour-6 §22 slice gate.
