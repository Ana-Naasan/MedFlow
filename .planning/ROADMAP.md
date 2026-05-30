# Roadmap: Umraa — Polypharmacy Decision Packet

## Overview

A ~24h, four-person build of a clinical decision-support backend and two React apps that ingest a patient's record from heterogeneous institution sources through read-only connectors, normalize to a FHIR R4 subset, cache in Postgres with TTL refresh, flatten to a citation-tagged context, and run a Gemini reasoning core that surfaces deterministically-verified, cited hypotheses linking symptoms↔drugs/interactions/conditions/procedures. The journey mirrors `docs/PRD.md`: lay foundations and the shared contracts (M0), prove the spine end-to-end at the hour-6 gate (M1), widen to the flagship integration and interaction story (M2), add enrichment and depth (M3), then harden and freeze for the demo (M4). The non-negotiable invariant runs through every phase — no resolvable citation, not shown.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Contracts (M0 Setup)** - Repo/CI/Docker scaffold, FHIR subset + flattener, Provider contract, and the OpenAPI/typed-client stub that unblocks every connector and the frontend
- [ ] **Phase 2: Hour-6 Vertical Slice (M1)** - The PRD §22 gate: MockFHIR → cache → flatten → reason → ≥1 verified cited hypothesis → /packet → rendered clickable citation in the provider app
- [ ] **Phase 3: Core (M2)** - RxNav normalization + DDInter interactions, the two-institution Postgres generality story, intake app, and knowledge-citation panel
- [ ] **Phase 4: Enrichment (M3)** - PDF span-highlight + HL7v2 scaffold connectors, Beers/STOPP + ACB knowledge, the full cross-reference differential with source-derived tiers, and missing-data UI
- [ ] **Phase 5: Polish & Freeze (M4)** - Keyboard review flow, structured logging/observability, feature freeze, pre-warmed cache, and recorded fallback

## Phase Details

### Phase 1: Foundation & Contracts (M0 Setup)
**Goal**: The shared spine everything builds on exists and is proven: the FHIR subset validates, the flattener is deterministic, the Provider contract is fixed, and the OpenAPI contract stub generates a typed frontend client — so all connectors and the frontend can develop in parallel from here.
**Depends on**: Nothing (first phase)
**Requirements**: FHIR-01, FHIR-02, FHIR-03, FHIR-04, CONN-01, CONN-06, SEC-02, SEC-03, API-08, FE-07, INFRA-01, INFRA-02, INFRA-04
**Success Criteria** (what must be TRUE):
  1. From a clean clone, `docker-compose up` brings up the app + `institution_a` + `institution_b` Postgres, the backend serves `/health` + `/docs`, the frontend boots with `next dev`, and `pytest` runs green.
  2. The system builds and `model_validate()`s one instance of all 6 R4B resources via `fhir.resources.R4B.*`, and Synthea `urn:uuid:` refs resolve to stable `ResourceType/id` literals.
  3. The deterministic flattener renders a hand-written bundle to markdown with every line tagged `[ResourceType/id]`, always rendering every clinical category with explicit status (raw FHIR JSON is never produced for the LLM).
  4. The Provider ABC + `Capability` flags + `FetchResult`/`Provenance`/`HealthStatus` dataclasses + registry-dict factory exist with the `ConnectorError` hierarchy and `coverage` contract, and a developer can run `gen:api` to produce a typed (`openapi-fetch` + `openapi-react-query`) client from the OpenAPI 3.1 DTO schema.
  5. CI runs backend lint + typecheck + `pytest` with a coverage gate on `reasoning/` and `provider`, plus frontend lint + `tsc` + build, and blocks merge on red; `main` is protected (PR + ≥1 review + green checks + CODEOWNERS).
**Critical path / dependency notes**:
  - This phase is the fan-out point. The Provider ABC + `FetchResult`/`Provenance` dataclasses + the DTO/OpenAPI contract unblock ALL connectors (Phases 2–4) AND the frontend — the frontend develops against the typed client generated from the contract stub, in parallel, before any real endpoint exists.
  - The FHIR subset (FHIR-01/02) feeds the flattener (FHIR-03/04), which feeds the reasoning core (Phase 2). Build order: subset builders + validate-all-6 → flattener against a hand-written bundle (PRD §23 steps 1–2). The R4B import gotcha must be killed here.
  - SEC-02 (MRN-keyed minimization, age-from-DOB, no name/address/phone/next-of-kin into reasoning) is a contract baked into the subset/flattener now so downstream reasoning never sees minimized fields.
  - API-08 / FE-07 establish `separate_input_output_schemas=False` slim DTOs so TS codegen doesn't choke on raw FHIR.
**Plans**: TBD
**UI hint**: yes

### Phase 2: Hour-6 Vertical Slice (M1)
**Goal**: The end-to-end spine runs green and is demoable: a real connector pull produces a verified, cited hypothesis that renders in the provider app with a citation that resolves on click. This is the PRD §22 gate and the project's survival floor.
**Depends on**: Phase 1
**Requirements**: CONN-02, CACHE-01, CACHE-02, CACHE-03, CACHE-04, KNOW-02, REASON-01, REASON-02, REASON-08, API-01, API-02, API-03, API-04, API-05, API-07, FE-01, DATA-01
**Success Criteria** (what must be TRUE):
  1. The full §22 slice runs end-to-end: `MockFHIRProvider.fetch_patient(hero)` → FHIR subset Bundle → cache upsert → flatten (tagged) → reasoning (openFDA single-drug) → ≥1 verified cited hypothesis → `GET /patients/{id}/packet` → rendered in the provider app with a clickable citation that resolves.
  2. The Postgres cache stores one JSONB row per resource with idempotent upsert, refresh-on-read works via TTL `expires_at` + `pg_try_advisory_xact_lock` (winner re-pulls, others serve cache), and the response sets `X-Cache: HIT|REFRESH`; every connector read writes an `audit_event` row.
  3. The deterministic verifier drops any hypothesis whose patient citation isn't in cache or whose openFDA evidence-card ref wasn't actually fetched, and when zero hypotheses survive the packet returns "no well-supported explanation found" (never invents).
  4. A clinician can click a patient-fact citation chip and resolve it via `GET /patients/{id}/resource/{rtype}/{fhir_id}`, and a knowledge citation via `GET /evidence/{card_id}`, with `HTTPBearer` dev-token auth rendering Swagger Authorize and CORS allowing `localhost:3000`.
  5. The hero (and backup) synthetic patient exists with a clinically plausible planted interaction and deterministic hard-coded RxCUIs, so the slice is reproducible for the demo without the public FHIR server.
**Critical path / dependency notes**:
  - All items in this phase are P0. MockFHIR connector (CONN-02) + cache (CACHE-01/02/03/04) are the M1 slice prerequisites; the chain FHIR subset → flattener (Phase 1) → reasoning core (REASON-01/02/08) → `/packet` endpoint (API-01) → provider-app packet view (FE-01) is the spine.
  - openFDA single-drug (KNOW-02) is the only knowledge source needed for the slice (records carry `openfda.rxcui` + `openfda.generic_name`); responses are cached and recorded as fixtures so CI runs without live API.
  - **PRD §22 gate rule (mandatory):** if the slice is not green by hour 6, STOP adding connectors and harden the slice. Cut connectors in order **HL7v2 → PDF → Postgres** (falling back to 2 real + 2 scaffold) and reduce the coverage gate to "core tests exist."
  - Two-tier quality bar applies hard here: the reasoning core, verifier, cache refresh-on-read, and citation resolution are correctness-critical — full tests + cross-pair review + coverage gate.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Core (M2)
**Goal**: The headline "aha" and the integration story are real: drugs normalize to RxNorm, drug-pair interactions surface as cited hypotheses, two deliberately-different institution schemas flow through one PostgresProvider to prove generality, the intake app submits sources, and knowledge citations open a readable side panel.
**Depends on**: Phase 2 (green slice)
**Requirements**: KNOW-01, KNOW-03, CONN-03, DATA-02, DATA-03, SEC-01, REASON-07, API-06, FE-03, FE-04
**Success Criteria** (what must be TRUE):
  1. Each medication normalizes to RxCUI (+ ingredient RxCUI + ATC) via RxNav, unresolved meds are flagged (never silently dropped), and below Tier 1 the packet states "limited input — low confidence."
  2. DDInter drug-pair interactions surface as cited interaction hypotheses, bridged from RxNorm via RxNav name/ATC with an unresolved-drug-flagged fallback.
  3. The same `PostgresProvider` reads two different seeded institution schemas (A and B) through explicit per-institution mappers producing identical FHIR, demonstrating generality with no DSL.
  4. Institution DB access uses a SELECT-only role + `SET TRANSACTION READ ONLY` and no connector exposes a write method; knowledge datasets are vendored into `seeds/`.
  5. A clinician can open a knowledge citation chip to a side panel showing the openFDA/Beers snippet + deep link, and the patient intake app submits to `/intake`; `confirm`/`dismiss` record audited clinician decisions.
**Critical path / dependency notes**:
  - RxNav normalization (KNOW-01) BLOCKS DDInter interaction hypotheses (KNOW-03) — DDInter/Beers/ACB are keyed by name/ingredient/ATC, not RxCUI, so the RxNav bridge is the prerequisite hop (the one fuzzy seam, needs the flagged fallback).
  - PostgresProvider (CONN-03) + the two institution seeds/mappers (DATA-02) BLOCK the two-institution generality demo — the flagship real-world integration story.
  - DATA-03 (vendored DDInter CSV, ACB list, Beers/STOPP JSON, Synthea bundle, frozen PDF) underpins both KNOW work here and PDF/Beers work in Phase 4.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Enrichment (M3)
**Goal**: The product shows its full depth: the PDF connector delivers the span-highlight citation moment, the HL7v2 scaffold is honestly framed, geriatric knowledge (Beers/STOPP, ACB) deepens the differential, hypotheses carry source-derived confidence tiers across the full cross-reference taxonomy, and missing data becomes explicit clinician action items.
**Depends on**: Phase 2 (a green slice) and Phase 3 (RxNav/knowledge + Postgres)
**Requirements**: CONN-04, CONN-05, KNOW-04, KNOW-05, REASON-03, REASON-04, REASON-05, REASON-06, FE-02, FE-05
**Success Criteria** (what must be TRUE):
  1. The PDFProvider extracts the frozen text-layer clinical PDF via `pdfplumber` + `langextract` → FHIR, persists char-offset spans into `Provenance.span`, and a patient-fact citation chip jumps to the PDF page with the span highlighted (or the chart row if Postgres-sourced).
  2. The HL7v2Provider scaffold parses one ADT message → `Patient` demographics, framed openly as scaffolded.
  3. Beers/STOPP geriatric rules and the ACB anticholinergic-burden list surface as cited hypotheses, and each surviving hypothesis carries a confidence tier derived from its source (the §12 ladder, never self-reported; pure-speculative dropped or loudly flagged).
  4. The engine produces a differential of competing explanations across entity types (drug↔symptom, drug↔drug, drug↔condition, drug↔age, allergy↔drug, lab↔drug, condition→symptom, procedure→symptom), with symptom text ↔ MedDRA reaction terms matched via curated synonym match against the FAERS terms openFDA returned, gated by the verifier.
  5. Missing-data rules hold (never assert safety from absence; downgrade confidence on missing fields; emit explicit "data gap / unknowns" items), and a per-category data-completeness indicator surfaces gaps as clinician action items.
**Critical path / dependency notes**:
  - Everything in this phase is blocked-by a green Phase 2 slice — M3 widens the spine, it does not replace it. If the slice regresses, M3 work pauses.
  - PDF connector (CONN-04) is the §8 cut-order penultimate; HL7v2 (CONN-05) is first to cut. Both are framed as widen-after-hour-6 work and must not jeopardize the spine.
  - REASON-03/04/05/06 lean on the knowledge layer from Phase 3 (RxNav/openFDA/DDInter) plus the new Beers/ACB sources; the verifier (Phase 2) gates the fuzzy symptom↔MedDRA seam.
  - Two-tier quality bar: connector→FHIR mappers (incl. PDF span provenance) and the knowledge joins are correctness-critical (full tests + coverage); confidence-tier labeling and missing-data UI are correctness-critical for the trust story too.
**Plans**: TBD
**UI hint**: yes

### Phase 5: Polish & Freeze (M4)
**Goal**: The demo is fast, observable, and bulletproof: the provider review flow is fully keyboard-driven, partial-data warnings are surfaced via structured logging, and the build is frozen with a pre-warmed cache and a recorded fallback so nothing can break on stage.
**Depends on**: Phase 4
**Requirements**: FE-06, INFRA-03, INFRA-05
**Success Criteria** (what must be TRUE):
  1. The provider review flow is fully keyboard-driven (approve / dismiss / next) with managed focus.
  2. Structured logging surfaces partial-data warnings and observability over the `ConnectorError` hierarchy.
  3. The demo is frozen: feature freeze in effect, cache pre-warmed, a seeded-local primary path plus a recorded fallback run, and a dry-run checklist exists.
**Critical path / dependency notes**:
  - Polish/enrichment ships fast under the two-tier bar — these items do not require the full coverage gate, only that they work for the demo.
  - INFRA-05 (freeze, pre-warm, recorded fallback) is the last gate; per PRD §21 the cache is pre-warmed and a live ~10–15s "gathering" refresh pass is optional flourish, not the primary path.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Contracts (M0) | 0/TBD | Not started | - |
| 2. Hour-6 Vertical Slice (M1) | 0/TBD | Not started | - |
| 3. Core (M2) | 0/TBD | Not started | - |
| 4. Enrichment (M3) | 0/TBD | Not started | - |
| 5. Polish & Freeze (M4) | 0/TBD | Not started | - |
