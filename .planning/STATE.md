# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Last activity: 2026-05-31 — working the merge queue one PR at a time (Claude deep-review per PR; Copilot errored/conflict-skipped on several). **MERGED #58** (MockFHIR, CONN-02, #11) + **#55** (Postgres cache, #12). For #55 I extended the PR with refresh-on-read (CACHE-02/03): `expires_at` TTL + `get_or_refresh` under `pg_try_advisory_xact_lock` returning a `CacheStatus` for X-Cache, tz-safe expiry; then resolved a `requirements.txt` conflict vs planning by merging planning into the branch (kept `fhirpy 2.2.0` + `aiosqlite`) — that conflict was why `pull_request` CI was silently skipping (no mergeable commit). Full 5-package gate 100% on py3.12; backend CI green; approved + admin squash-merged. Set up **PR #62** (Claude auto-review Action — needs Bader to install the app + add a secret). Earlier: M0 validation audit (`phases/01-.../01-VALIDATION.md`) + quick task 260531-2sh (FE-07 + openapi regen, **PR #61**). Remaining audit gaps: no backend mypy in CI / CODEOWNERS routes only `.planning/`. **Follow-up owed:** wire `get_or_refresh` + X-Cache into `api/packet.py` off the `store.py` stand-in.

Progress (Phase 1 / M0): [██████████] ~97% — M0 substantively complete; merge queue draining (#58, #55 in). Spilling into M1 prerequisites (MockFHIR + cache landed).

**Branch model:** `planning` = protected dev branch (PR + 1 review; teammates fully gated); `main` = submission branch. `.planning/` is owned by **@B2707 only** (CODEOWNERS + code-owner review; owner pushes `.planning` updates directly).

### Open PRs / In Review (working the queue one-by-one this session)

- **#60 (#23 PostgresProvider, ha/issue-23, Hamza)** — MIS-TITLED "Database cache" but actually the **PostgresProvider hospital connector (CONN-03, M2)** + two institution SQL schemas (Copilot confirmed). NOT the cache (that was #55). Touches `providers/__init__.py` → WILL conflict with merged #58; needs a planning merge. M2/Phase-3 scope.
- **#56 (#14 openFDA drug-safety, feat/drug-safety-openfda-14)** — reasoning/knowledge runtime; gate requires `app/knowledge`+`app/reasoning` at 100%. NEXT.
- **#61 (FE-07 + openapi.json, feat/fe07-openapi-contract, Bader)** — closes the two material M0 audit gaps; frontend lint+tsc+vitest green (7/7), code-only branch, no AI-trace watermarks. Ready to merge.
- **#59 (#27 PDF connector, feat/pdf-connector)** — CONN-04 char-offset provenance; Phase 4/M3 work. Review last.
- **#62 (ci: Claude auto-review workflow, ci/claude-auto-review, Bader)** — adds the Claude GitHub Action; merge after Bader installs the app + secret.

### Done (on `planning`, green) — this session's merges

- **#11 MockFHIR connector (PR #58, merged `b124bfd`)** — `providers/mock_fhir.py` `MockFHIRProvider` (CONN-02): snapshot-first HAPI R4 fetch, trims+validates the 6 types, honest coverage/provenance, ABC-conformant. Fix-forward applied (partial flag, fhirpy 2.2.0, dropped aiosqlite). `app/providers` 100% on py3.12.
- **#12 Postgres cache (PR #55, merged `dfc63ee`)** — `cache/models.py` (CachedResource/EvidenceCard/AuditEvent, JSONB↔JSON variant), `cache/repo.py`: idempotent upsert (CACHE-01), audit-on-read (CACHE-04), **refresh-on-read (CACHE-02/03)** — `expires_at` TTL + `get_or_refresh` under `pg_try_advisory_xact_lock` (winner re-pulls, losers serve cache) → `CacheStatus` for X-Cache, tz-safe expiry. Extended by Bader during review; requirements conflict vs planning resolved. `app/cache` 100% on py3.12. Follow-up: wire into `api/packet.py` off the `store.py` stand-in.

### Done (on `planning`, green)

- #1 spike — all 6 FHIR R4B resources import + `model_validate` (8 tests)
- #2 scaffold — runnable monorepo (backend `/health`+`/docs`, frontend, docker-compose 3× Postgres)
- #3 Provider ABC — registry + FetchResult/Provenance/HealthStatus + ConnectorError + coverage contract (11 tests). The fan-out unblocker.
- #4 DTO/OpenAPI contract — Citation/Hypothesis/DecisionPacket DTOs + `/packet` stub + regenerated typed client (PR #45). Frontend can now build against the typed client.
- #7 CI — backend + frontend pipelines, coverage gate scaffolded (relaxed to 0 until core code lands)
- #9 config + docker — required-secret config guard + `.env` placeholders (PR #46) AND the docker-compose backend service wired in (PR #54, issue #9 CLOSED). Real Gemini/openFDA keys still go in local `.env` to exercise the runtime.
- #17 packet API (PR #51) — `/patients`, `/packet` (X-Cache:HIT), citation-resolution (`/resource/...`, `/evidence/...`), `/refresh`, `/connectors`, HTTPBearer dev-auth, CORS; in-memory `cache/store.py` stand-in (replaced by #12/#55). Black fix pushed to Hamza's branch (7106c63) with his OK.
- #5/#6/#28/#21-followup — FHIR subset+minimize (#48), flattener (#52), HL7v2 scaffold (#50), seed-data RxCUI corrections (#53).
- **Core 100% coverage + gate (PR #57)** — `test_coverage_branches.py` (27 branch tests) → `fhir/providers/cache/knowledge/reasoning` at 100%; dead `fhir/flattener.py` deleted; CI `--cov-fail-under=100` on those packages. Verify coverage on **Python 3.12** only (local 3.9 gives a false ~13%; the project uses `UTC`/`slots`).
- #21 seed data — DDInter (10k interaction pairs), ACB scale, AGS 2023 Beers, Synthea sample FHIR bundle + text-layer clinical PDF vendored to `backend/app/seeds/` with provenance (SOURCES.md) + typed loaders + 26 tests (PR #47). Synthetic data only.
- #5 FHIR subset — `fhir/subset.py` (6 validated R4B builders via `fhir.resources.R4B.*` killing the R5-default gotcha + `reasoning_view` SEC-02 minimization: strips name/address/telecom/contact, drops birthDate→`ageYears`, keeps MRN-only identifiers, recursive incl. contained, non-mutating) + `fhir/references.py` (`urn:uuid:`→`ResourceType/id`, non-mutating) + 26 tests (PR #48). Full suite green. Unblocks #6, #11.
- #6 flattener (FHIR-03/04) — `fhir/flatten.py` `flatten_to_tagged_text`: deterministic (fixed category order, NKA-aware), every category always rendered (present / `(stated as none by source)` / `(not documented)`), every clinical line tagged `[ResourceType/id]`, never emits raw FHIR JSON. + 190 lines of tests (PR #52). Closes the citation-tagged-context gap; feeds the Phase 2 reasoning core.
- #28 HL7v2 scaffold — `providers/hl7v2.py` `HL7v2Provider`: parses one ADT^A01 PID → FHIR Patient demographics, `partial=True` + explicit scaffold warning, honest coverage dict, `ConnectorDataError` on bad input, conforms to the Provider ABC + 18 tests (PR #50). The §8 'first to cut' connector, honestly framed.
- #17 packet API slice — `api/packet.py` (/patients, /{id}/packet w/ X-Cache:HIT, /{id}/resource/{rtype}/{id} + /evidence/{id} citation resolution, /{id}/refresh w/ X-Cache:REFRESH, /connectors) + `api/auth.py` (HTTPBearer dev-token) + CORS localhost:3000 + 3 tests (PR #51). Runs against an in-memory STAND-IN (`cache/store.py` static data) — real cache (#12) + reasoning (#14) replace it. NOTE: `cache/store.py` + `auth.py` will collide with #12/#13/dev-auth work — reconcile when building those.
- #21 follow-up (PR #53) — corrected `acb.json` (every ingredient RxCUI re-derived from RxNav; the prior file collided RxCUIs across distinct drugs — 41493×4, 3498, 3489, 354770 — which would mis-key the ACB bridge; nortriptyline deduped to published grade 1; 74 drugs, 0 dup names/RxCUIs) + `SOURCES.md` (bundle med list corrected — no warfarin in the bundle; planted interaction is in the PDF + Beers rule; dropped uncommitted generator-script path). Resolves the Copilot data findings from #47.
- Core 100% coverage (PR #57) — `test_coverage_branches.py` (27 branch tests) brings `fhir/providers/cache/knowledge/reasoning` to 100% line coverage; deleted dead `fhir/flattener.py`; CI gate raised to `--cov-fail-under=100` on those packages (two-tier bar). Verified on py3.12 (CI runtime) = 100.00%, 365 stmts, 0 missed. NOTE: coverage must be measured on **Python 3.12** — local 3.9 can't import the code (UTC/slots), gives a false ~13%.

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

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260531-2sh | FE-07 typed-client wiring + regenerate stale openapi.json (M0 contract gaps; PR #61) | 2026-05-31 | 4ce80e7 | [260531-2sh-fix-fe-07-typed-client-wiring-and-regene](./quick/260531-2sh-fix-fe-07-typed-client-wiring-and-regene/) |

### Phase 1 / M0 Validation Audit (2026-05-31)

Goal-backward audit vs the 5 success criteria + 14 requirements → `phases/01-foundation-contracts-m0-setup/01-VALIDATION.md`. **M0 substantively COMPLETE** on merged code (FHIR subset, deterministic flattener, SEC-02 minimization, Provider contract, OpenAPI/typed-client path all proven at the 100% gate). 4 in-repo gaps found; 2 material ones closed in PR #61 (FE-07, stale openapi.json). **2 remaining (minor, fix-or-accept at the phase-boundary gate):** no backend typecheck/mypy in CI (INFRA-02); CODEOWNERS routes only `.planning/` (INFRA-04). OPS-01 real-key provisioning (Hamza) is external, not a code gap.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-31
Stopped at: Phase 1 (M0) ~90%. Cleared the ENTIRE PR queue (6 PRs, full flow each): #47 (#21 seeds), #48 (#5 FHIR subset), #53 (#21 fix-forward), #52 (#6 flattener), #50 (#28 HL7v2), #51 (#17 packet API). `planning`=4cf9f15, synced, tree clean, 0 open PRs. (Pushed #51's black fix to Hamza's branch with his OK; briefly mis-diagnosed a MockFHIR blocker that didn't exist — corrected.)
Resume file: None
Next: (1) **Determine whether Phase 1/M0 is actually COMPLETE** — PR queue is empty but verify M0 requirements (FHIR-01..04, CONN-01/06, SEC-02/03, API-08, FE-07, INFRA-01/02/04, OPS-01) are all delivered before declaring done. #9/OPS-01 (real Gemini/openFDA keys) is the likely outstanding M0 item — it stays open pending key provisioning by Hamza. (2) Once M0 is genuinely complete → run the PHASE-BOUNDARY REVIEW GATE (Blockers section): code-review → verify-work → secure-phase → add-tests, fix-forward, THEN advance to Phase 2. (3) Phase 2 work: #12 cache (M1 §22 prerequisite; reconcile w/ #51's stand-in cache/store.py), #23 Postgres, #33 observability; #14/#15 reasoning core (has flattener input, needs keys via #9). Watch the hour-6 §22 slice gate.
