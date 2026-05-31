# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Last activity: 2026-05-31 — big PR-queue clearing pass (each: code+test+Copilot review → approve → admin squash-merge → close). Merged #47 (#21 seeds), #48 (#5 FHIR subset), #53 (fix-forward for #21 Copilot data findings), #52 (#6 flattener — closes the FHIR-03/04 gap), #50 (#28 HL7v2 scaffold). **#51 (#17 packet API) held — CI red on `black --check`** (router.py/auth.py/cache/store.py); commented the fix to Hamza, not merged.

Progress (Phase 1 / M0): [████████░░] ~80%

**Branch model:** `planning` = protected dev branch (PR + 1 review; teammates fully gated); `main` = submission branch. `.planning/` is owned by **@B2707 only** (CODEOWNERS + code-owner review; owner pushes `.planning` updates directly).

### Open PRs / In Review

- **#51 (#17 hour-6 packet API slice, Hamza) — BLOCKED on CI**: `black --check` wants to reformat `backend/app/api/router.py`, `api/auth.py`, `cache/store.py` (ruff + tests pass; formatting only). Commented the one-line fix (`black .` + push); will review + merge once green. NOTE: this PR also introduces `cache/store.py` + `api/auth.py` — overlaps Bader's #12 cache / dev-auth territory; review for divergence before merge.

### Done (on `planning`, green)

- #1 spike — all 6 FHIR R4B resources import + `model_validate` (8 tests)
- #2 scaffold — runnable monorepo (backend `/health`+`/docs`, frontend, docker-compose 3× Postgres)
- #3 Provider ABC — registry + FetchResult/Provenance/HealthStatus + ConnectorError + coverage contract (11 tests). The fan-out unblocker.
- #4 DTO/OpenAPI contract — Citation/Hypothesis/DecisionPacket DTOs + `/packet` stub + regenerated typed client (PR #45). Frontend can now build against the typed client.
- #7 CI — backend + frontend pipelines, coverage gate scaffolded (relaxed to 0 until core code lands)
- #9 (partial) — required-secret config guard + `.env` placeholders merged (PR #46). #9 stays OPEN until real Gemini/openFDA keys are provisioned in local `.env`.
- #21 seed data — DDInter (10k interaction pairs), ACB scale, AGS 2023 Beers, Synthea sample FHIR bundle + text-layer clinical PDF vendored to `backend/app/seeds/` with provenance (SOURCES.md) + typed loaders + 26 tests (PR #47). Synthetic data only.
- #5 FHIR subset — `fhir/subset.py` (6 validated R4B builders via `fhir.resources.R4B.*` killing the R5-default gotcha + `reasoning_view` SEC-02 minimization: strips name/address/telecom/contact, drops birthDate→`ageYears`, keeps MRN-only identifiers, recursive incl. contained, non-mutating) + `fhir/references.py` (`urn:uuid:`→`ResourceType/id`, non-mutating) + 26 tests (PR #48). Full suite green. Unblocks #6, #11.
- #6 flattener (FHIR-03/04) — `fhir/flatten.py` `flatten_to_tagged_text`: deterministic (fixed category order, NKA-aware), every category always rendered (present / `(stated as none by source)` / `(not documented)`), every clinical line tagged `[ResourceType/id]`, never emits raw FHIR JSON. + 190 lines of tests (PR #52). Closes the citation-tagged-context gap; feeds the Phase 2 reasoning core.
- #28 HL7v2 scaffold — `providers/hl7v2.py` `HL7v2Provider`: parses one ADT^A01 PID → FHIR Patient demographics, `partial=True` + explicit scaffold warning, honest coverage dict, `ConnectorDataError` on bad input, conforms to the Provider ABC + 18 tests (PR #50). The §8 'first to cut' connector, honestly framed.
- #21 follow-up (PR #53) — corrected `acb.json` (every ingredient RxCUI re-derived from RxNav; the prior file collided RxCUIs across distinct drugs — 41493×4, 3498, 3489, 354770 — which would mis-key the ACB bridge; nortriptyline deduped to published grade 1; 74 drugs, 0 dup names/RxCUIs) + `SOURCES.md` (bundle med list corrected — no warfarin in the bundle; planted interaction is in the PDF + Beers rule; dropped uncommitted generator-script path). Resolves the Copilot data findings from #47.

### Ready / unblocked now

- #11 (Mohammad) — unblocked by #5 FHIR subset now merged
- #14/#15 reasoning core — the flattener (#6) now feeds it the tagged context; still needs Gemini keys (#9)
- #12 cache (Bader), #23 Postgres connector (Bader+Hamza), #33 observability (Bader)
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

Copilot data findings from #21 — RESOLVED in PR #53 (merged). Remaining are cosmetic-only, deferred (not worth a PR; mention to Mohammad if touching the file):
- [#5 / Mohammad, cosmetic] `fhir/references.py` `resolve_references` is annotated `dict[str, Any]` but intentionally passes non-dict through; the Copilot autofix corrected the docstrings to `Any` pre-merge but not the annotation. No mypy in CI, so harmless.
- [#5 / Mohammad, cosmetic] `reasoning_view` docstring example hard-codes `ageYears = 36` (date-dependent; not a live doctest). Swap to a stable assertion if editing.

### Blockers/Concerns

- [Phase 1 — CRITICAL PATH]: #3 Provider ABC, #4 DTO/OpenAPI, #5 FHIR subset, #21 seed data all MERGED ✓ — M0 fan-out complete: connectors, cache, frontend, knowledge, reasoning inputs all unblocked. Remaining Bader critical-path code: #12 cache (M1 §22 slice prerequisite), #23 Postgres connector, #17 API, #33 observability.
- [Phase 1 — GAP RESOLVED]: deterministic **flattener (FHIR-03/04)** landed via PR #52 (issue #6, `fhir/flatten.py`) — the citation-tagged context for the Phase 2 reasoning core now exists.
- [Process]: `planning` is protected (PR + 1 review). Flow per PR = code review + test run → formal approve → admin squash-merge → close issue+PR. **Take the Copilot bot review into account every time** (it caught a valid SEC-02 gap on #48 — author fixed it pre-merge in commit `bdcc3948` — plus the #21 data nits now in Pending Todos). Watch for AI-trace watermarks: PR #44 had `Co-Authored-By: Claude`+`🤖`; PR #48 had per-commit `Co-authored-by: Copilot Autofix` trailers — all dropped by squash (verified clean on the squash commits). No Claude/AI references anywhere per project policy.
- [Process — git]: `gh pr merge --squash` mutates `origin` server-side; ALWAYS `git fetch && git reset --hard origin/planning` before the next local `.planning` doc-sync commit, or a stale-branch push reverts the merge (a stale STATE push was correctly rejected non-fast-forward this session; recovered).
- [Phase 2]: The hour-6 §22 gate is the survival floor — the MockFHIR → cache → flatten → reason → verified cited hypothesis → /packet → rendered clickable citation chain must be green before widening. Watch the clock; apply the cut order if at risk.
- [Phase 3]: RxNav→DDInter/Beers/ACB bridge is keyed by name/ingredient/ATC (not RxCUI) — a string/class match with miss risk (salts, synonyms, combos); needs the flagged fallback and manual verification for demo drugs.
- [PHASE-BOUNDARY REVIEW GATE — standing rule, user-directed 2026-05-31]: Before advancing from ANY phase (1→2, 2→3, …) to the next, run a full multi-agent review over that phase's merged code, in order: (1) `/gsd-code-review` (bugs + quality), (2) `/gsd-verify-work` (every ROADMAP success criterion actually TRUE — the spec/"no mistakes" check), (3) `/gsd-secure-phase` (threat + SEC-02 PHI-minimization / read-only / no-secrets audit), (4) `/gsd-add-tests` (coverage gaps on critical-path code). Findings → fix-forward via the standard review→approve→merge flow, THEN advance. Do NOT run the gate until the phase is actually complete (e.g. Phase 1 is NOT done while PR #51/#17 is open).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-31
Stopped at: Phase 1 (M0) ~80%. Cleared 5 PRs through the full flow (code+test+Copilot review → approve → admin squash-merge → close): #47 (#21 seeds), #48 (#5 FHIR subset), #53 (fix-forward for #21 data findings), #52 (#6 flattener), #50 (#28 HL7v2). Flattener gap resolved. `planning`=761ff99, synced, tree clean. **#51 (#17 packet API) is the only thing keeping Phase 1 open — held on a `black --check` CI failure, fix commented to Hamza.**
Resume file: None
Next: (1) re-review + merge #51 once Hamza pushes the black fix (watch its `cache/store.py`+`auth.py` overlap with #12/#13). (2) **Phase 1 is then COMPLETE → run the PHASE-BOUNDARY REVIEW GATE (see Blockers): code-review → verify-work → secure-phase → add-tests, fix-forward, THEN advance to Phase 2.** (3) Phase 2 work: #12 cache (M1 §22 prerequisite), #23 Postgres connector, #33 observability; #14/#15 reasoning core (has flattener input, needs Gemini keys via #9). Watch the hour-6 §22 slice gate.
