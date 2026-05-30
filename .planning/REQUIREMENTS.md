# Requirements: Umraa — Polypharmacy Decision Packet

**Defined:** 2026-05-30
**Core Value:** Every clinical claim surfaced to the UI carries a resolvable citation to a real source; the deterministic verifier guarantees no fabricated fact or citation reaches the clinician.

> Requirements trace to `docs/PRD.md`. Phase mapping mirrors the PRD §22 hour-6 gate and §23 build order, grouped into the milestones M0 Setup → M1 Hour-6 Slice → M2 Core → M3 Enrichment → M4 Polish & Freeze.

## v1 Requirements

### FHIR — Unified schema & flattener (PRD §4, §10)

- [ ] **FHIR-01**: System builds and validates one instance of all 6 R4B resources (Patient, MedicationStatement, Condition, Observation, AllergyIntolerance, Procedure) via `fhir.resources.R4B.*` with `model_validate()` at every connector boundary
- [ ] **FHIR-02**: Synthea `urn:uuid:` references are resolved to stable `ResourceType/id` literals on ingest so citations are stable
- [ ] **FHIR-03**: Deterministic template flattener renders the FHIR subset to markdown with every line tagged `[ResourceType/id]` (raw FHIR JSON is never fed to the LLM)
- [ ] **FHIR-04**: Flattener always renders every clinical category with explicit status and never silently omits an absent category

### CONN — Connectors / Provider layer (PRD §7, §8)

- [ ] **CONN-01**: Provider `abc.ABC` + `Capability` flags + `FetchResult`/`Provenance`/`HealthStatus` dataclasses + registry-dict factory form the shared read-only contract every connector implements
- [ ] **CONN-02**: `MockFHIRProvider` fetches from HAPI `baseR4` via `fhirpy`, projects to the subset, re-validates, and caches a local snapshot so the demo never depends on the public server
- [ ] **CONN-03**: `PostgresProvider` reads two deliberately-different institution schemas (A and B) through explicit per-institution mapper functions producing identical FHIR
- [ ] **CONN-04**: `PDFProvider` extracts a frozen text-layer clinical PDF via `pdfplumber` + `langextract` → FHIR, persisting char-offset spans into `Provenance.span`
- [ ] **CONN-05**: `HL7v2Provider` scaffold parses one ADT message → `Patient` demographics (+`AL1`→`AllergyIntolerance` if cheap), framed openly as scaffolded
- [ ] **CONN-06**: `FetchResult.coverage` records which resource types each source supports vs returned, and partial fetches return what they could with `partial=True` + warnings (never a zeroed bundle); source errors normalize to a `ConnectorError` hierarchy

### CACHE — Postgres cache & audit (PRD §9)

- [ ] **CACHE-01**: `cached_resource` JSONB store holds one row per FHIR resource with idempotent upsert (`on_conflict_do_update`)
- [ ] **CACHE-02**: Synchronous refresh-on-read uses TTL `expires_at` + `pg_try_advisory_xact_lock`; winner re-pulls and upserts while others serve cache; response sets `X-Cache: HIT|REFRESH`
- [ ] **CACHE-03**: An `audit_event` row is written on every connector read (projects to FHIR AuditEvent)
- [ ] **CACHE-04**: `evidence_card` store persists external knowledge snippets, each citable by a stable id

### KNOW — Drug-knowledge lookups (PRD §6, §11.3)

- [ ] **KNOW-01**: RxNav normalizes each medication to RxCUI (+ ingredient RxCUI + ATC); medications that don't resolve are flagged, never silently dropped
- [ ] **KNOW-02**: openFDA single-drug adverse-reaction + label lookup keyed by `rxcui`/`generic_name`, with response caching and recorded fixtures for tests (no live API in CI)
- [ ] **KNOW-03**: DDInter drug-pair interaction lookup, bridged from RxNorm via RxNav name/ATC match with an unresolved-drug-flagged fallback
- [ ] **KNOW-04**: Beers/STOPP geriatric rule lookup from transcribed JSON rules (AGS attributed)
- [ ] **KNOW-05**: ACB anticholinergic-burden lookup from the static vendored list

### REASON — Reasoning core & guardrails (PRD §11–§16)

- [ ] **REASON-01**: One Gemini reasoning call consumes the flattened closed-world context + evidence cards and returns structured JSON hypotheses citing `[ResourceType/id]` tags + evidence-card ids
- [ ] **REASON-02**: Deterministic verifier drops any hypothesis whose patient or knowledge citations don't resolve (every patient id exists in cache; every external ref is a fetched card; PDF quotes appear in source text) — the structural anti-hallucination guarantee
- [ ] **REASON-03**: Each surviving hypothesis is assigned a confidence tier from its source (the §12 ladder), never self-reported; pure-speculative is dropped or loudly flagged
- [ ] **REASON-04**: Engine produces a differential of competing explanations across entity types (drug↔symptom, drug↔drug, drug↔condition, drug↔age, allergy↔drug, lab↔drug, condition→symptom, procedure→symptom)
- [ ] **REASON-05**: Patient symptom text ↔ MedDRA reaction term matched via a curated synonym/string match against the FAERS terms openFDA returned, gated by the verifier
- [ ] **REASON-06**: Missing-data reasoning rules — never assert safety from absence, downgrade confidence of hypotheses depending on a missing field, and emit explicit "data gap / unknowns" items (absence = unknown, never "none")
- [ ] **REASON-07**: Minimum-input contract enforced — below Tier 1 the packet states "limited input — low confidence"; every medication must resolve to RxNorm or be flagged
- [ ] **REASON-08**: Abstention — when zero hypotheses survive verification, return "no well-supported explanation found," never invent

### API — FastAPI + OpenAPI surface (PRD §14, §17)

- [ ] **API-01**: `GET /patients/{id}/packet` returns a `DecisionPacket` (summary markdown + cited hypotheses + data gaps + cache info) with the `X-Cache` header
- [ ] **API-02**: `GET /patients/{id}/resource/{rtype}/{fhir_id}` resolves a patient-fact citation, including `source_span` when PDF-sourced
- [ ] **API-03**: `GET /evidence/{card_id}` resolves a knowledge citation to its snippet + ref_url
- [ ] **API-04**: `POST /patients/{id}/refresh` forces a connector re-pull (demo button)
- [ ] **API-05**: `GET /patients`, `GET /connectors` (registered providers + health + capabilities), and `GET /audit` are served
- [ ] **API-06**: `POST /intake` seeds a source; `POST /hypotheses/{id}/confirm` and `/dismiss` record audited clinician decisions
- [ ] **API-07**: `HTTPBearer` dev-token auth (renders Swagger Authorize; subject → audit actor) and CORS allowing `localhost:3000`
- [ ] **API-08**: OpenAPI 3.1 schema exposes slim Pydantic DTOs (`Citation`, `Hypothesis`, `DecisionPacket`) with `separate_input_output_schemas=False`; typed client generated via `gen:api`

### FE — Frontend apps (PRD §14, §18)

- [ ] **FE-01**: Provider decision-packet app renders hypothesis cards (why-line, severity, confidence tier) with at least one clickable citation that resolves
- [ ] **FE-02**: Patient-fact citation chips link into the source — PDF page with the span highlighted (via `source_span`) or the chart row if Postgres-sourced
- [ ] **FE-03**: Knowledge citation chips open a side panel showing the openFDA/Beers snippet + deep link
- [ ] **FE-04**: Patient intake app submits to `/intake`
- [ ] **FE-05**: Per-category data-completeness indicator surfaces data gaps as clinician action items
- [ ] **FE-06**: Provider review flow is fully keyboard-driven (approve / dismiss / next) with managed focus
- [ ] **FE-07**: Typed API client (`openapi-fetch` + `openapi-react-query`) wires a global bearer middleware and is generated from the OpenAPI contract

### DATA — Seed data (PRD §6, §24)

- [ ] **DATA-01**: A hero (and backup) synthetic patient exists across different source documents with a clinically plausible planted interaction and deterministic hard-coded RxCUIs
- [ ] **DATA-02**: Two institution Postgres seed schemas (A and B, deliberately different) plus their mappers prove generality
- [ ] **DATA-03**: Knowledge datasets are vendored into `seeds/` — DDInter CSV, ACB list, transcribed Beers/STOPP JSON, one Synthea R4 bundle, one frozen clinical PDF

### SEC — Security / PHI posture (PRD §20)

- [ ] **SEC-01**: Institution DB access uses a SELECT-only role + `SET TRANSACTION READ ONLY`; no connector exposes a write method
- [ ] **SEC-02**: Data minimization — reasoning keys on MRN, derives age from DOB, and never pulls name/address/phone/next-of-kin into the reasoning context
- [ ] **SEC-03**: Synthetic data only; no secrets in the repo; `.env` discipline with a committed `.env.example`

### INFRA — Repo, CI, ops (PRD §19, build process)

- [ ] **INFRA-01**: Runnable monorepo scaffold — backend boots (`uvicorn` serves `/health` + `/docs`), frontend boots (`next dev`), `docker-compose up` brings up app + `institution_a` + `institution_b` Postgres, and tests run green from a clean clone
- [ ] **INFRA-02**: CI runs on every PR — backend lint + typecheck + `pytest` with a coverage gate on core packages (`reasoning/`, `provider`); frontend lint + `tsc` + tests + build — and blocks merge on any red check
- [ ] **INFRA-03**: Structured logging and surfaced partial-data warnings (observability over the `ConnectorError` hierarchy)
- [ ] **INFRA-04**: `main` is protected (PR + ≥1 review + green required checks + squash/linear history) with `CODEOWNERS` routing reviewers by area
- [ ] **INFRA-05**: Demo freeze — feature freeze, pre-warmed cache, seeded-local primary plus a recorded fallback run, and a dry-run checklist

### OPS — DevOps & external services (PRD §3, §24) — owner: Hamza

- [ ] **OPS-01**: External-service provisioning & secrets wiring — a Google Cloud project + Gemini API credentials (`google-genai`), an openFDA API key, and the dev token are provisioned and wired through `.env` (with a committed `.env.example` per PRD §24), so the reasoning core and knowledge lookups run from a clean clone
- [ ] **OPS-02**: Demo hosting/deployment — the app (API + app Postgres) is deployed to the chosen target (Vultr or Google Cloud) for the live demo, with the seeded-local + recorded-fallback path kept as the guaranteed primary (PRD §3 deploy is optional, §21–§22 freeze); optional, do not let it jeopardize the spine

## v2 Requirements

Deferred — tracked, not in the v1 roadmap.

### Knowledge & reasoning depth

- **V2-01**: Full HL7v2-to-FHIR coverage via the HL7 v2-to-FHIR IG / LinuxForHealth
- **V2-02**: Database-grounded condition/procedure→symptom links (SNOMED graph reasoning)
- **V2-03**: OCR for image-only PDFs
- **V2-04**: `Coverage` (insurance) and `patient-citizenship` extension mapped into the served model
- **V2-05**: Optional embedding *suggestion* for symptom↔MedDRA matching (verifier-gated, never source of truth)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vector database / semantic retrieval | One patient fits whole in context; knowledge joins are exact key lookups — similarity would guess where an exact join is a fact (PRD §11) |
| Connector write paths | Connectors are strictly read-only; institution stays system of record (PRD §1, §20) |
| Real PHI | Synthetic data only; Gemini calls carry no identifiers (PRD §20) |
| Reasoning over name/address/phone/next-of-kin | Read for realism, never pulled into reasoning; key on MRN, derive age from DOB (PRD §5) |
| SNOMED graph grounding (v1) | Too heavy for the timebox; condition/procedure links anchored to cited resources and tiered low instead (PRD §12) |
| Demo script / pitch / team logistics | This is a technical build spec only (PRD scope note) |

## Traceability

Phase mapping mirrors PRD §22 (hour-6 gate) and §23 (build order). Mapped into ROADMAP.md on 2026-05-30 — every v1 requirement assigned to exactly one phase, no orphans, no duplicates.

| Requirement | Phase | Milestone | Status |
|-------------|-------|-----------|--------|
| FHIR-01 | Phase 1 | M0 Setup | Pending |
| FHIR-02 | Phase 1 | M0 Setup | Pending |
| FHIR-03 | Phase 1 | M0 Setup | Pending |
| FHIR-04 | Phase 1 | M0 Setup | Pending |
| CONN-01 | Phase 1 | M0 Setup | Pending |
| CONN-06 | Phase 1 | M0 Setup | Pending |
| SEC-02 | Phase 1 | M0 Setup | Pending |
| SEC-03 | Phase 1 | M0 Setup | Pending |
| API-08 | Phase 1 | M0 Setup | Pending |
| FE-07 | Phase 1 | M0 Setup | Pending |
| INFRA-01 | Phase 1 | M0 Setup | Pending |
| INFRA-02 | Phase 1 | M0 Setup | Pending |
| INFRA-04 | Phase 1 | M0 Setup | Pending |
| OPS-01 | Phase 1 | M0 Setup | Pending |
| CONN-02 | Phase 2 | M1 Hour-6 Slice | Pending |
| CACHE-01 | Phase 2 | M1 Hour-6 Slice | Pending |
| CACHE-02 | Phase 2 | M1 Hour-6 Slice | Pending |
| CACHE-03 | Phase 2 | M1 Hour-6 Slice | Pending |
| CACHE-04 | Phase 2 | M1 Hour-6 Slice | Pending |
| KNOW-02 | Phase 2 | M1 Hour-6 Slice | Pending |
| REASON-01 | Phase 2 | M1 Hour-6 Slice | Pending |
| REASON-02 | Phase 2 | M1 Hour-6 Slice | Pending |
| REASON-08 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-01 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-02 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-03 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-04 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-05 | Phase 2 | M1 Hour-6 Slice | Pending |
| API-07 | Phase 2 | M1 Hour-6 Slice | Pending |
| FE-01 | Phase 2 | M1 Hour-6 Slice | Pending |
| DATA-01 | Phase 2 | M1 Hour-6 Slice | Pending |
| KNOW-01 | Phase 3 | M2 Core | Pending |
| KNOW-03 | Phase 3 | M2 Core | Pending |
| CONN-03 | Phase 3 | M2 Core | Pending |
| DATA-02 | Phase 3 | M2 Core | Pending |
| DATA-03 | Phase 3 | M2 Core | Pending |
| SEC-01 | Phase 3 | M2 Core | Pending |
| REASON-07 | Phase 3 | M2 Core | Pending |
| API-06 | Phase 3 | M2 Core | Pending |
| FE-03 | Phase 3 | M2 Core | Pending |
| FE-04 | Phase 3 | M2 Core | Pending |
| CONN-04 | Phase 4 | M3 Enrichment | Pending |
| CONN-05 | Phase 4 | M3 Enrichment | Pending |
| KNOW-04 | Phase 4 | M3 Enrichment | Pending |
| KNOW-05 | Phase 4 | M3 Enrichment | Pending |
| REASON-03 | Phase 4 | M3 Enrichment | Pending |
| REASON-04 | Phase 4 | M3 Enrichment | Pending |
| REASON-05 | Phase 4 | M3 Enrichment | Pending |
| REASON-06 | Phase 4 | M3 Enrichment | Pending |
| FE-02 | Phase 4 | M3 Enrichment | Pending |
| FE-05 | Phase 4 | M3 Enrichment | Pending |
| FE-06 | Phase 5 | M4 Polish & Freeze | Pending |
| INFRA-03 | Phase 5 | M4 Polish & Freeze | Pending |
| INFRA-05 | Phase 5 | M4 Polish & Freeze | Pending |
| OPS-02 | Phase 5 | M4 Polish & Freeze | Pending |

**Coverage:**
- v1 requirements: 55 total (FHIR 4, CONN 6, CACHE 4, KNOW 5, REASON 8, API 8, FE 7, DATA 3, SEC 3, INFRA 5, OPS 2)
- Mapped to phases: 55
- Unmapped: 0 ✓

> Note: the prior "51 total" figure was an undercount of the same checklist; the verified per-category sum was 53. OPS-01/OPS-02 (DevOps & external-service provisioning, owner Hamza) were added 2026-05-30, bringing the total to 55. All map to exactly one phase.

---
*Requirements defined: 2026-05-30*
*Last updated: 2026-05-30 — phase mapping confirmed in ROADMAP.md (53/53 mapped, no orphans, no duplicates)*
