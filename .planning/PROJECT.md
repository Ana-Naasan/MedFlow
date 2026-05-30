# Umraa — Polypharmacy Decision Packet

## What This Is

A clinical decision-support backend and two React apps that ingest a patient's record from heterogeneous medical-institution sources through pluggable read-only **connectors**, normalize everything into a unified **FHIR R4 subset**, cache it in Postgres with TTL refresh, flatten it into a citation-tagged context, and run a **Gemini reasoning core** that surfaces **cited hypotheses** cross-referencing the patient's current symptoms against their drugs, drug–drug interactions, conditions, and procedures. The AI gathers and connects; the clinician decides. It is built for providers reviewing polypharmacy risk in elderly/complex patients, plus a patient-intake surface.

## Core Value

Every clinical claim surfaced to the UI carries a resolvable citation to a real source — no resolvable citation, not shown. The differential of cited, tiered hypotheses linking symptoms↔drugs/interactions/conditions/procedures is the product; the deterministic anti-hallucination verifier is what makes it trustworthy. If everything else fails, the hour-6 vertical slice (mock FHIR → cache → flatten → reason → ≥1 verified cited hypothesis → `/packet` → rendered clickable citation) must work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. Full detail in REQUIREMENTS.md. -->

- [ ] Unified FHIR R4 subset (6 resources) with validation + deterministic citation-tagged flattener
- [ ] Provider abstraction (ABC + registry + FetchResult/Provenance contract) — the shared interface that unblocks all connectors and the frontend
- [ ] Connectors: MockFHIR (build first), PostgresProvider (two institution schemas), PDFProvider (frozen file, span provenance), HL7v2 scaffold
- [ ] Postgres cache with refresh-on-read (TTL + advisory lock), upsert idempotency, AuditEvent on every read
- [ ] Drug-knowledge lookups: RxNav normalization, openFDA, DDInter pairs, Beers/STOPP, ACB — joined by exact key, no vector DB
- [ ] Reasoning core: single Gemini call producing structured cited hypotheses across the cross-reference taxonomy with source-derived confidence tiers
- [ ] Deterministic verifier that drops any hypothesis with an unresolvable patient or knowledge citation (the structural anti-hallucination guarantee)
- [ ] Missing-data handling: absence = unknown (never "none"); explicit data-gap items
- [ ] FastAPI + OpenAPI 3.1 with slim DTOs, HTTPBearer dev auth, and citation-resolution endpoints
- [ ] Provider decision-packet app (hypothesis cards, citation chips, PDF-span highlight, keyboard review flow)
- [ ] Patient intake app + `/intake`
- [ ] Seed data: hero + backup synthetic patient across different sources with a planted, clinically plausible interaction; two institution DB schemas; vendored knowledge datasets

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Vector database / semantic retrieval — one patient fits whole in context; knowledge joins are exact key lookups, so similarity would be guessing where an exact join is a fact (PRD §11)
- Connector write paths — connectors are strictly read-only; the institution stays system of record (PRD §1, §20)
- Real PHI — synthetic data only; Gemini calls carry no identifiers (PRD §20)
- OCR / image-only PDFs — PDFProvider handles text-layer PDFs only (PRD §8)
- SNOMED graph grounding for condition/procedure→symptom links — too heavy for the timebox; these links are anchored to the patient's cited resources and tiered low instead (PRD §12)
- Reasoning over name/address/phone/next-of-kin — read for realism but never pulled into reasoning; we key on MRN and derive age from DOB (PRD §5, §20)
- Full HL7v2-to-FHIR coverage — scaffold only; full coverage via HL7 v2-to-FHIR IG / LinuxForHealth is roadmap (PRD §8)
- Coverage (insurance) and citizenship resources — seeded for realism but outside the 6-resource clinical subset (PRD §5)
- Demo script / pitch / team logistics — this is a technical build spec only

## Context

- **Event:** MPC Hacks 2026, Dialogue track — a time-boxed (~24h) multi-person build. Process must protect the demo, not strangle it.
- **Team (4):** Platform pair — Bader (@B2707) + Hamza (@HamzaAlsarakbi); Reasoning pair — Mohammad (@MohammadESteitieh) + Vivek (@VMotta1). Platform owns repo/CI/Docker, the Provider ABC + DTO/OpenAPI contracts, Mock FHIR + Postgres connectors, cache, API, and both React apps. Reasoning owns the FHIR subset + flattener, reasoning core + verifier, knowledge lookups, cross-reference taxonomy/confidence tiers, citation payloads, the PDF connector, missing-data rules, and the hero/backup patient clinical content.
- **Authoritative spec:** `docs/PRD.md` is the source of truth for architecture, the FHIR subset, the connector/cache/reasoning design, the build order (§23), and the hour-6 vertical-slice gate (§22). These `.planning/` artifacts are the GSD translation of that spec and become canonical once verified complete.
- **Real-world framing:** drug knowledge is easy/public; patient-data access (institutional integration) is the genuinely hard part — exactly what the connector layer + "sit with IT, write a read-only connector mapping their DB to our FHIR schema" story addresses (mirrors Redox / 1upHealth / Mirth).
- **Verified facts (2026-05-30):** `fhir.resources==8.2.0` imports R4 via `fhir.resources.R4B.*` (root package is R5); openFDA records carry `openfda.rxcui` + `openfda.generic_name`; RxNav is RxNorm-native; DDInter/Beers/ACB are keyed by drug name/ingredient/ATC (bridge via RxNav).

## Constraints

- **Tech stack (backend):** FastAPI (OpenAPI 3.1), `fhir.resources==8.2.0` (import `fhir.resources.R4B.*`), SQLAlchemy 2.x async + asyncpg, PostgreSQL 16, `google-genai`, `fhirpy` 2.2.0, `hl7apy` 1.3.5, `pdfplumber` 0.11.x, `langextract` 1.2.0, httpx, pydantic v2 — all pinned (PRD §3).
- **Tech stack (frontend):** Next.js/React + TS, TanStack Query 5.x, `openapi-typescript` 7.13.0 + `openapi-fetch` 0.17.0 + `openapi-react-query` 0.5.4; typed client via `gen:api` (PRD §3, §18).
- **Infra:** `docker-compose` with three Postgres services — app DB + `institution_a` + `institution_b` (the last two read-only-roleable external sources) (PRD §19).
- **Timeline:** ~24h. Critical path first (M0 + M1). If M1 isn't green by hour 6, cut connectors in order **HL7v2 → PDF → Postgres** and reduce the coverage gate to "core tests exist" (PRD §22).
- **Performance:** cold ≈10–20s (dominated by the single LLM call), warm sub-second–8s; pre-warm the cache for the demo (PRD §21).
- **Security/PHI:** read-only DB role + `SET TRANSACTION READ ONLY`; MRN-keyed minimization; transient TTL cache; AuditEvent on every read; synthetic-only data; no secrets in repo (PRD §20).
- **Non-negotiable invariant:** no resolvable citation → not shown; output language is always "may be associated — consider reviewing," never "caused by"/"stop drug X"; absence of data = unknown, never "none."

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FHIR R4 subset of exactly 6 resources, imported via `fhir.resources.R4B.*` | Enough to reason about drug↔symptom↔condition↔procedure and to cite; R4B import avoids the R5-default gotcha | — Pending |
| Provider `abc.ABC` + registry-dict factory, built **first** | We own all impls; shared helpers + runtime enforcement; unblocks every connector and (via the OpenAPI contract) the frontend in parallel | — Pending |
| No vector database anywhere | One patient fits whole in context; knowledge joins are exact key lookups; citations must be yes/no membership checks, not similarity scores | — Pending |
| Anti-hallucination is structural: deterministic post-generation verifier drops unresolved citations | You cannot make an LLM never hallucinate; you architect so anything hallucinated is caught and dropped before the UI | — Pending |
| Generality proven by two different institution Postgres schemas through one `PostgresProvider` (explicit per-connector mappers, no DSL) | Debuggable; proves the integration story without a generic engine | — Pending |
| Expose slim Pydantic DTOs, not raw FHIR | Raw FHIR blows up TS codegen; `separate_input_output_schemas=False` | — Pending |
| Hour-6 vertical-slice gate with explicit connector cut order | Time-boxed build; protect the demo spine before widening | — Pending |
| Two-tier quality bar: correctness-critical (verifier, mappers, cache, citation resolution, knowledge joins) get full tests + cross-pair review + coverage gate; polish/enrichment ship fast | Process protects the demo, not strangles it | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-30 after initialization*
