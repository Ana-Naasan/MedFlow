# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Last activity: 2026-05-31 — reviewed + merged PR #47 (#21 drug-knowledge seed data + loaders). #4/#9 contracts already in. One PR (#48, #5 FHIR subset) still open in review.

Progress (Phase 1 / M0): [█████░░░░░] ~50%

**Branch model:** `planning` = protected dev branch (PR + 1 review; teammates fully gated); `main` = submission branch. `.planning/` is owned by **@B2707 only** (CODEOWNERS + code-owner review; owner pushes `.planning` updates directly).

### Open PRs / In Review

- #48 (#5 FHIR subset builders + validation + MRN minimization, Mohammad) — under review

### Done (on `planning`, green)

- #1 spike — all 6 FHIR R4B resources import + `model_validate` (8 tests)
- #2 scaffold — runnable monorepo (backend `/health`+`/docs`, frontend, docker-compose 3× Postgres)
- #3 Provider ABC — registry + FetchResult/Provenance/HealthStatus + ConnectorError + coverage contract (11 tests). The fan-out unblocker.
- #4 DTO/OpenAPI contract — Citation/Hypothesis/DecisionPacket DTOs + `/packet` stub + regenerated typed client (PR #45). Frontend can now build against the typed client.
- #7 CI — backend + frontend pipelines, coverage gate scaffolded (relaxed to 0 until core code lands)
- #9 (partial) — required-secret config guard + `.env` placeholders merged (PR #46). #9 stays OPEN until real Gemini/openFDA keys are provisioned in local `.env`.
- #21 seed data — DDInter (10k interaction pairs), ACB scale, AGS 2023 Beers, Synthea sample FHIR bundle + text-layer clinical PDF vendored to `backend/app/seeds/` with provenance (SOURCES.md) + typed loaders + 26 tests (PR #47). Synthetic data only.

### Ready / unblocked now

- #5 FHIR subset (Mohammad) — starter posted on the issue; blocks #6, #11
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

None yet.

### Blockers/Concerns

- [Phase 1 — CRITICAL PATH]: #3 (Provider ABC) is MERGED ✓ — unblocked the connectors + cache. **#4 (DTO/OpenAPI contract, @B2707) is now the top remaining bottleneck** — it blocks the API (#17) and all frontend (#19/#24/#25). Land #4 next. Also #5 (FHIR subset, Mohammad) unblocks #6/#11.
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
Stopped at: Phase 1 (M0) ~50%. Working the PR queue one at a time with full code+test review before merge. PR #47 (#21 drug-knowledge seeds) reviewed (clean, 26 tests, no AI traces) + merged via owner-admin (squash). PR #48 (#5 FHIR subset) is next in the queue.
Resume file: None
Next: review PR #48 (#5 FHIR subset builders + validation + MRN minimization) end-to-end, then merge/close. Then pick up Bader's unblocked critical-path issues — #12 cache, #23 Postgres connector, #33 observability. Watch the hour-6 §22 slice gate.
