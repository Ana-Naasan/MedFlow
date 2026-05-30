# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-05-30 — Roadmap created from PRD (5 phases mirroring M0–M4); 55/55 v1 requirements mapped (added OPS-01/02 DevOps track, owner Hamza)

Progress: [░░░░░░░░░░] 0%

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

- [Phase 2]: The hour-6 §22 gate is the survival floor — the MockFHIR → cache → flatten → reason → verified cited hypothesis → /packet → rendered clickable citation chain must be green before widening. Watch the clock; apply the cut order if at risk.
- [Phase 3]: RxNav→DDInter/Beers/ACB bridge is keyed by name/ingredient/ATC (not RxCUI) — a string/class match with miss risk (salts, synonyms, combos); needs the flagged fallback and manual verification for demo drugs.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-30
Stopped at: ROADMAP.md and STATE.md created; REQUIREMENTS.md traceability confirmed (55/55 mapped)
Resume file: None
