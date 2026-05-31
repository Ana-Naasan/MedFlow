# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Last activity: 2026-05-31 — PR #44 (Provider ABC / connector interface, #3) opened and reviewed; scaffold + CI green on `planning`; spike #1 done

Progress (Phase 1 / M0): [███░░░░░░░] ~30%

**Branch model:** `planning` = protected dev/integration branch (PR + 1 review required, no direct pushes); `main` = submission branch (promote `planning → main` when verified).

### Open PRs / In Review

| PR | Issue | Title | Author | CI | Review |
|----|-------|-------|--------|----|--------|
| #44 | #3 | Provider ABC / connector interface (registry, errors, 11 tests) | @B2707 | ✅ green | Reviewed (2 minor notes) — needs 1 teammate approval to merge |

### Done (on `planning`, green)

- #1 spike — all 6 FHIR R4B resources import + `model_validate` (8 tests)
- #2 scaffold — runnable monorepo (backend `/health`+`/docs`, frontend, docker-compose 3× Postgres)
- #7 CI — backend + frontend pipelines, coverage gate scaffolded (relaxed to 0 until core code lands)

### In flight

- #9 provisioning (Hamza) — Gemini/openFDA keys; blocks reasoning runtime (#14, #15)
- #5 FHIR subset (Mohammad) — Ready, starter posted; blocks #6, #11
- #4 DTO/OpenAPI contract (Bader) — Ready; blocks API (#17) + all frontend

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

None yet.

### Blockers/Concerns

- [Phase 1 — CRITICAL PATH]: #3 (Provider ABC, in review as PR #44) and #4 (DTO/OpenAPI contract) — both @B2707 — are the fan-out point. Until merged, all connectors (#11/#23/#27/#28), the cache→API chain (#12→#17), and all frontend (#19/#24/#25) stay blocked. Fastest team unblock = land #3 + #4.
- [Process]: `planning` is protected (PR + 1 review). Every PR gets a code review before merge; watch for AI-trace watermarks (PR #44 arrived with `Co-Authored-By: Claude` + `🤖 Generated with Claude Code` — both stripped). No Claude/AI references anywhere per project policy.
- [Phase 2]: The hour-6 §22 gate is the survival floor — the MockFHIR → cache → flatten → reason → verified cited hypothesis → /packet → rendered clickable citation chain must be green before widening. Watch the clock; apply the cut order if at risk.
- [Phase 3]: RxNav→DDInter/Beers/ACB bridge is keyed by name/ingredient/ATC (not RxCUI) — a string/class match with miss risk (salts, synonyms, combos); needs the flagged fallback and manual verification for demo drugs.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-31
Stopped at: Phase 1 execution underway. PR #44 (#3 Provider ABC) reviewed + cleaned (AI traces stripped), CI green, awaiting 1 teammate approval. STATE synced with open-PR tracking.
Resume file: None
Next: land #3 (#44) + #4 to unblock the team; review incoming PRs (code review before merge); move issues across the board as PRs open/merge.
