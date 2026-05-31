# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-30)

**Core value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown; the deterministic verifier is what makes it trustworthy.
**Current focus:** Phase 1 — Foundation & Contracts (M0 Setup)

## Current Position

Phase: 1 of 5 (Foundation & Contracts — M0 Setup)
Status: In progress — team executing against GitHub issues on the `planning` dev branch
Latest (resume session, 2026-05-31): **merged #59 PDF connector** (fix-forward off a 4-lens adversarial review — MedicationStatement remap + dose-reaches-reasoning fix + provenance-invariant fix + 100% gate) and **#62/#70 Claude auto-review Action** (now live on every non-draft PR). Board reconciled: #14/#13/#23/#27 → Done. Open queue now just **#63 (observability)** + **#68 (deployment, DRAFT)**.
Last activity: 2026-05-31 — working the merge queue one PR at a time (Claude deep-review per PR; Copilot errored/conflict-skipped on several). **MERGED #58** (MockFHIR, CONN-02, #11) + **#55** (Postgres cache, #12) + **#56** (openFDA, KNOW-02, #14). For #56 I rewrote the connector to REAL openFDA shapes (verified via a research workflow): per-seriousness counts via filtered total queries (not the fabricated meta.results the old code read), reaction frequency via `count=patient.reaction.reactionmeddrapt.exact`. An adversarial review workflow then caught 2 HIGH bugs the fixture suite masked — malformed `+AND+` encoding (httpx → `%2BAND%2B`) and a Lucene-injection hole in `_escape_value` — both fixed + locked with tests; MEDIUM hardening tracked in **#65**. Also set GSD to **Opus for every agent** (model_overrides) per user mandate, and **code-review depth = deep**. For #55 I extended the PR with refresh-on-read (CACHE-02/03): `expires_at` TTL + `get_or_refresh` under `pg_try_advisory_xact_lock` returning a `CacheStatus` for X-Cache, tz-safe expiry; then resolved a `requirements.txt` conflict vs planning by merging planning into the branch (kept `fhirpy 2.2.0` + `aiosqlite`) — that conflict was why `pull_request` CI was silently skipping (no mergeable commit). Full 5-package gate 100% on py3.12; backend CI green; approved + admin squash-merged. Set up **PR #62** (Claude auto-review Action — needs Bader to install the app + add a secret). Earlier: M0 validation audit (`phases/01-.../01-VALIDATION.md`) + quick task 260531-2sh (FE-07 + openapi regen, **PR #61**). Remaining audit gaps: no backend mypy in CI / CODEOWNERS routes only `.planning/`. **Follow-up owed:** wire `get_or_refresh` + X-Cache into `api/packet.py` off the `store.py` stand-in.

Progress (Phase 1 / M0): [██████████] 100% — M0 complete. **M1 §22-slice SPINE COMPLETE on `planning`:** MockFHIR (#58) → cache+refresh-on-read (#55/#64) → openFDA (#56) → `/packet` with `X-Cache: HIT|REFRESH|MISS`. **+ M2 PostgresProvider (#60).** 6 PRs merged this session (#58/#55/#56/#61/#64/#60). Remaining queue is M3/M4 widen work (#59 PDF, #63 observability) + #62 (CI, needs admin).

**This session merged (6 PRs):** #58 MockFHIR (CONN-02), #55 cache (CACHE-01/02/03/04), #56 openFDA (KNOW-02), #61 FE-07+openapi (M0 audit gaps), #64 X-Cache /packet wiring (#13), #60 PostgresProvider (CONN-03/M2). Each: Claude deep-review (+ adversarial workflow for correctness-critical) → fix-forward → approve → admin squash-merge → close. Follow-ups: #65 (openFDA hardening), #66 (cache→API), #67 (PostgresProvider integration/hardening). **M0 + M1 §22 slice spine + the M2 two-institution connector are all on `planning`.**

**Branch model:** `planning` = protected dev branch (PR + 1 review; teammates fully gated); `main` = submission branch. `.planning/` is owned by **@B2707 only** (CODEOWNERS + code-owner review; owner pushes `.planning` updates directly).

### Open PRs / In Review (widen-after-slice work; M3/M4)

- **#63 (#33 observability, feat/observability-partial-warnings-33, Bader)** — structured logging + partial-data warning surfacing. M4/Phase-5. Not yet reviewed.
- **#68 (chore: adding deployment, ha/deployment, Hamza)** — DRAFT (not ready); deployment infra (OPS-02, M4). Review when un-drafted.

> **#59 and #62 MERGED this session — see "Done (cont.)" below. The Claude auto-review Action is now live: every non-draft PR (#63, #68-once-ready, and all future) is auto-reviewed by Opus with no reviewer assignment (PR #62 + #70).**

### Open follow-up issues (non-blocking)
- **#65** — openFDA hardening (malformed-data safety, Retry-After, serious-umbrella, raw_* aliasing, id determinism, bucket lock).
- **#66** — cache→API (live-PG concurrency test for the once-only guarantee, `cache_status` single-source, non-pat-001 packets).
- **#67** — PostgresProvider integration/hardening (registry wiring + `/connectors` off the static list, R4B model round-trip, coverage/partial honesty, SELECT-only role wiring, deeper A==B + integration tests, pool race).

### Done (on `planning`, green) — this session (continued 2026-05-31, resume)

- **#27 PDF connector (PR #59, merged `59b44a5`)** — `providers/pdf.py` `PDFProvider` (CONN-04): text-layer PDF → Patient/Condition/MedicationStatement with exact **char-offset provenance** (`page_text[start:end] == snippet`). Fix-forward earned by a 4-lens adversarial review: (1) meds emitted `MedicationRequest` (NOT in the 6-resource subset → silently dropped by flatten/reason) → remapped to **valid-R4B `MedicationStatement`** (status+subject+dosage); (2) the review caught that `flatten._dose()` read only structured `doseQuantity` so the PDF's free-text dose was **silently dropped before reasoning** → added a `dosage[].text` fallback in `flatten.py` so dose/route/indication reaches the Gemini context (verified end-to-end on the planted Warfarin+Aspirin pair); (3) latent provenance-invariant break (snippet stripped vs unstripped offsets) → `_trimmed_span` helper; (4) the test fixture path was CWD-relative (broke under CI's `cd backend`) → anchored to `__file__`. `pdf.py` 92%→**100%**; full gate 100% on py3.12; CI green. Closed #27, card→Done.
- **Claude auto-review Action (PR #62 merged `529d799`, PR #70 merged `5559ace`)** — `.github/workflows/claude-code-review.yml`: Opus orchestrator fans out 4 per-dimension review subagents + adversarial verify, posts inline comments + a PASS/CONCERNS/BLOCK verdict on **every non-draft PR** (opened/synchronize/reopened/ready_for_review — no reviewer assignment). Uses `pull_request` (not `pull_request_target`), job-scoped least-priv perms, restricted tool allowlist. Now live: default branch = `planning`, `CLAUDE_CODE_OAUTH_TOKEN` secret installed (Bader did the one-time app+secret setup — the prior blocker is resolved). LOW follow-up: `@claude review` on-demand comment trigger not wired (needs an `issue_comment` event).

### Done (on `planning`, green) — earlier this session's merges

- **#11 MockFHIR connector (PR #58, merged `b124bfd`)** — `providers/mock_fhir.py` `MockFHIRProvider` (CONN-02): snapshot-first HAPI R4 fetch, trims+validates the 6 types, honest coverage/provenance, ABC-conformant. Fix-forward applied (partial flag, fhirpy 2.2.0, dropped aiosqlite). `app/providers` 100% on py3.12.
- **#12 Postgres cache (PR #55, merged `dfc63ee`)** — `cache/models.py` (CachedResource/EvidenceCard/AuditEvent, JSONB↔JSON variant), `cache/repo.py`: idempotent upsert (CACHE-01), audit-on-read (CACHE-04), **refresh-on-read (CACHE-02/03)** — `expires_at` TTL + `get_or_refresh` under `pg_try_advisory_xact_lock` (winner re-pulls, losers serve cache) → `CacheStatus` for X-Cache, tz-safe expiry. Extended by Bader during review; requirements conflict vs planning resolved. `app/cache` 100% on py3.12. Follow-up: wire into `api/packet.py` off the `store.py` stand-in (covers issue #13 — see PR #64 overlap).
- **#14 openFDA connector (PR #56, merged `cd1607f`)** — `knowledge/openfda.py` (KNOW-02): adverse-event + label lookups; real-shaped queries (per-seriousness filtered totals, `count=` reaction frequency), evidence snippets with stable resolvable IDs, token-bucket + bounded TTL cache. Rewritten from fabricated `meta.results` shapes → real API; 2 HIGH review bugs fixed (AND encoding, Lucene injection). `app/knowledge` 100% on py3.12. Hardening follow-ups in #65.
- **FE-07 + openapi.json (PR #61, merged `b6bf763`)** — global bearer `.use()` middleware (per-request token) + `openapi-react-query` `$api`; `openapi.json` regenerated from the live API. Closes the two material M0 audit gaps (FE-07, API-08).
- **#13 X-Cache /packet wiring (PR #64, merged `3a443d0`)** — `api/packet.py` serves `/packet` via `repo.get_or_refresh` with `X-Cache: HIT|REFRESH|MISS`; lifespan-managed async engine + `session_factory`; `/refresh` upserts; `CACHE_TTL_SECONDS`. Completes the §22 slice spine. Fix-forward: removed MISS double-fetch; honest concurrency-test scope (live-PG test → #66).
- **Phase-1 M0 boundary gate + SEC-02/HL7v2 hardening (PR #69, merged `34a30ad`)** — `01-REVIEW.md` (4-Opus-dimension gate, no blockers) + fixes: `reasoning_view` minimisation now a **fail-closed allow-list** (only resourceType/id/gender/ageYears/MRN survive; Synthea text/photo/communication/maritalStatus/extension + unknown fields dropped — closes the un-enumerated-field PHI leak, SEC-02); HL7v2 raises `ConnectorDataError` on empty PID; flattener determinism + reference single-pass pinned by tests. Reviewed (Claude): allow-list PHI-tight + clinically sufficient. Gate 100% on py3.12.
- **#23 PostgresProvider (PR #60, merged `2e509ca`)** — `providers/postgres.py` (CONN-03/DATA-02): one provider reads two different institution schemas (`seeds/institution_a.sql`/`b.sql`) via explicit per-institution mappers → identical R4B; READ ONLY transactions (SEC-01 layer 1, tested); honest coverage/errors. Fix-forward: valid-R4B `valueQuantity` on missing units + coerced `Observation.status` (Inst B's overloaded `status_flag`). `app/providers` 100% on py3.12. Integration/hardening follow-ups in #67.

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

Last session: 2026-05-31 (resume)
Stopped at: `planning`=`5559ace`, synced, tree clean. This resume session merged **#59 PDF connector** (CONN-04; fix-forward off a 4-lens adversarial review — MedicationStatement remap, `flatten._dose()` text fallback so dose reaches reasoning, `_trimmed_span` provenance fix, CWD-safe fixture path, 100% gate), **#62 + #70 Claude auto-review Action** (live on every non-draft PR). Board reconciled: every closed issue (incl. #14/#13/#23/#27) is in Done on Project #3. Open PRs: **#63 observability** (not reviewed), **#68 deployment** (DRAFT).
Resume file: None
Next: (1) **Review/merge #63** (observability, M4) — it'll now get an automatic Claude review on its next push; do the human merge-gate too. (2) **#68 deployment** when Hamza un-drafts it. (3) Follow-ups still open: #65 (openFDA hardening), #66 (cache→API), #67 (PostgresProvider hardening); LOW: wire `@claude review` on-demand comment trigger into the review workflow (`issue_comment` event). (4) Confirm Phase-1/M0 completeness, then run the PHASE-BOUNDARY REVIEW GATE (code-review → verify-work → secure-phase → add-tests) before advancing to Phase 2. OPS-01 real-key provisioning may remain the last open M0 item.
