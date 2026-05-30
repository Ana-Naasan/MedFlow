# Technical PRD — Polypharmacy Decision Packet

**MPC Hacks 2026 · Dialogue track · Backend Python/FastAPI · Frontend React/TS · PostgreSQL · Gemini**

*Scope: technical architecture and build spec only — no demo script, pitch, or team logistics. All library versions and API facts verified live 2026-05-30.*

---

## 1. System overview

A clinical decision-support backend that ingests a patient's record from heterogeneous medical-institution sources through pluggable **connectors**, normalizes everything into a **unified FHIR R4 subset**, **caches** it in Postgres with TTL refresh, **flattens** it into a citation-tagged context, and runs a **Gemini reasoning core** that surfaces **cited hypotheses** cross-referencing the patient's current symptoms against their drugs, drug-drug interactions, conditions, and procedures. A typed REST API serves two React apps (patient intake, provider decision packet). The AI gathers and connects; the clinician decides.

**It is not just drugs:** the engine cross-references multiple entity types — meds, conditions/diseases, symptoms, procedures/surgeries, labs, allergies, age — and presents *competing explanations* for a finding (could be a drug, an interaction, the underlying disease, a post-surgical effect, a lab-gated risk). See §12.

**Non-functional invariants**
- Every clinical claim surfaced to the UI carries a citation to a source (`ResourceType/id` and/or an external knowledge record id). No resolvable citation → not shown (§13).
- Connectors are **read-only**. No connector exposes a write method.
- The institution remains system of record; our store is a **transient, session-scoped cache**.
- We key on **hospital number (MRN), never name**; personal info is read-but-not-reasoned-on (§5, §20).
- Absence of data = **unknown, never "none"** (§15).
- Output language is always *"may be associated — consider reviewing,"* never *"caused by"* / *"stop drug X."*

---

## 2. Architecture

```mermaid
flowchart TD
    subgraph Sources["External institution sources (read-only)"]
        S1[FHIR server\nHAPI baseR4]
        S2[Institution Postgres A]
        S3[Institution Postgres B]
        S4[Clinical PDF]
        S5[HL7v2 message]
    end
    subgraph Connectors["Provider layer (abc.ABC + registry)"]
        C1[MockFHIRProvider]
        C2[PostgresProvider]
        C4[PDFProvider]
        C5[HL7v2Provider scaffold]
    end
    S1-->C1
    S2-->C2
    S3-->C2
    S4-->C4
    S5-->C5
    C1 & C2 & C4 & C5 -->|FetchResult: FHIR Bundle + provenance| CACHE[(Postgres cache\ncached_resource JSONB + TTL)]
    CACHE -->|refresh-on-read if stale| Connectors
    CACHE --> FLAT[Deterministic flattener\nFHIR -> markdown w/ ResourceType/id tags]
    FLAT --> REASON[Reasoning core\nGemini + deterministic evidence lookups]
    subgraph Knowledge["Drug knowledge (external, cited by key)"]
        K1[openFDA FAERS + label]
        K2[DDInter CSV pairs]
        K3[RxNav RxNorm normalize]
        K4[Beers/STOPP rules]
        K5[ACB burden list]
    end
    REASON <-->|exact key lookups| K1 & K2 & K3 & K4 & K5
    REASON --> VERIFY[Deterministic verifier\ndrop any unresolved citation]
    VERIFY --> API[FastAPI + OpenAPI 3.1]
    API --> GEN[openapi-typescript client]
    GEN --> FE1[Provider decision-packet app]
    GEN --> FE2[Patient intake app]
    API --> AUDIT[(AuditEvent log)]
```

---

## 3. Tech stack (pinned)

| Layer | Choice | Version | Notes |
|---|---|---|---|
| Backend framework | FastAPI | 0.11x | OpenAPI 3.1 auto-gen; `/docs` Swagger |
| ASGI server | uvicorn | latest | |
| FHIR models | `fhir.resources` | ==8.2.0 | **import R4 via `fhir.resources.R4B.*`** (root pkg is R5) |
| DB driver | SQLAlchemy + asyncpg | SA 2.x, asyncpg 0.30.x | async; Core for external DBs |
| Postgres | PostgreSQL | 16 | JSONB + advisory locks |
| FHIR network client | `fhirpy` | 2.2.0 | Mock FHIR connector |
| HL7v2 parse | `hl7apy` | 1.3.5 | scaffold connector |
| PDF text | `pdfplumber` | 0.11.x | tables/layout; `pymupdf` if speed |
| PDF→structured | `langextract` + Gemini | 1.2.0 | char-offset source spans = citations |
| LLM | Gemini API | `google-genai` SDK | extraction + reasoning |
| Drug normalize | RxNav REST | n/a | free, no key |
| Frontend | Next.js / React + TS | 14/18 | |
| API client gen | openapi-typescript + openapi-fetch + openapi-react-query | 7.13.0 / 0.17.0 / 0.5.4 | types-only + thin runtime |
| Data fetching | TanStack Query | 5.x | |
| Deploy (optional) | Vultr | n/a | host the Postgres app |

**No vector database** anywhere — see §11.

---

## 4. Unified schema — FHIR R4 subset

Six clinical resources. Minimal fields = enough to reason about drug↔symptom↔condition↔procedure relationships and to cite. Imports use `fhir.resources.R4B.*`.

| Resource | Required-for-us fields | Purpose |
|---|---|---|
| **Patient** | `id`, `identifier` (MRN), `gender`, `birthDate` | age = core polypharmacy risk driver; MRN = join key |
| **MedicationStatement** (primary) | `id`, `status`, `medicationCodeableConcept` (RxNorm coding + `.text`), `subject`→Patient, `effectiveDateTime`/`effectivePeriod`, `dosage.text`, `reasonReference?`→Condition | actual meds taken; one per drug; the reasoning target |
| **Condition** | `id`, `clinicalStatus`, `code` (SNOMED/ICD + `.text`), `subject`→Patient, `onsetDateTime?` | comorbidities; symptom-vs-drug timing |
| **Observation** | `id`, `status`, `category`, `code` (LOINC + `.text`), `subject`→Patient, `effectiveDateTime`, `valueQuantity`/`valueCodeableConcept`, `interpretation?` | labs + vitals + **symptoms** |
| **AllergyIntolerance** | `id`, `clinicalStatus`, `code` (+`.text`), `patient`→Patient (note: `patient`, not `subject`), `reaction.manifestation?` | contraindication checks |
| **Procedure** (optional) | `id`, `status`, `code`, `subject`→Patient, `performedDateTime` | recent surgery/procedure context |

**References** are literal strings (`{"reference":"Patient/123"}`). Resolve Synthea `urn:uuid:` to `ResourceType/id` on ingest so citations are stable. **Validation:** `fhir.resources` Pydantic `model_validate()` at every connector boundary (raise on failure); HL7 Java validator only offline as a spot-check.

---

## 5. Patient demographic / administrative data contract

Two distinct field sets. A realistic hospital DB **guarantees** the full administrative set (so seeds look real and connectors have faithful targets); the reasoning **queries only** a minimized clinical subset. We key on **MRN, not name** (data minimization + matches real interop, which links by identifier).

| Field | In seed (realism)? | Queried into reasoning? | FHIR mapping | Mandatory for function? |
|---|---|---|---|---|
| Hospital number / MRN | ✅ required | ✅ — the join key | `Patient.identifier` | **YES** |
| DOB | ✅ required | ✅ — derive age | `Patient.birthDate` | **YES** (gates Beers/ACB) |
| Sex/gender | ✅ | ✅ | `Patient.gender` | recommended |
| Allergies | ✅ required | ✅ | `AllergyIntolerance` | strongly recommended (safety) |
| Medications | ✅ required | ✅ | `MedicationStatement` | **YES** |
| Conditions/diagnoses | ✅ | ✅ | `Condition` | enrichment |
| Labs/vitals/symptoms | ✅ | ✅ | `Observation` | ≥1 symptom required |
| Procedures/surgeries | ✅ | ✅ | `Procedure` | enrichment |
| Name | ✅ (realism) | ❌ | `Patient.name` (minimized) | no |
| Address | ✅ | ❌ | `Patient.address` | no |
| Phone | ✅ | ❌ | `Patient.telecom` | no |
| Relatives / next-of-kin | ✅ | ❌ | `Patient.contact` | no |
| Primary care physician | ✅ | ❌ (maybe UI header) | `Patient.generalPractitioner` | no |
| Insurance | ✅ | ❌ | `Coverage` (**outside the 6-resource subset** — seed only) | no |
| Citizenship | ✅ | ❌ | FHIR **extension** `patient-citizenship` (seed only) | no |

Note: insurance (`Coverage`) and citizenship (an extension) belong in the seed for realism but are not in our clinical subset — map only if time permits. Pitch line: *"We link on the hospital number, derive age from DOB, and never pull name/address/phone/next-of-kin into reasoning — minimum clinical data, nothing more."*

---

## 6. Data sources, acquisition & join keys

**No scraping anywhere** — official APIs, official dataset downloads, direct DB reads, local file parsing only.

| Source | How we get it | Key? | Difficulty | Note |
|---|---|---|---|---|
| openFDA (FAERS + labels) | REST API | Free key (120k/day) | Easy (verified) | rate-limit → cache; carries `rxcui`+`generic_name` in-band |
| RxNav / RxNorm | REST API | None | Easy (verified) | normalization backbone; `approximateTerm` for typos |
| DDInter (interaction pairs) | one-time CSV download | None | Easy | academic DB — cite it; not an API |
| ACB burden list | download (GitHub/PDF) | None | Easy | static list |
| Beers / STOPP-START | **manual transcription** → JSON rules | None | Moderate (small) | only hand-curation; attribute AGS |
| Patient — Mock FHIR | HAPI REST + Synthea bundles | None | Easy | cache a local snapshot for the demo |
| Patient — Postgres | SQL read (read-only role) | DSN | Easy (seeded) | — |
| Patient — PDF / HL7v2 | local file parse | None | Easy/Moderate | PDF fuzziest; frozen demo file |

**Join-key alignment (verified live):** RxNorm is the shared spine. FHIR `MedicationStatement` carries RxNorm; **openFDA records carry `openfda.rxcui` + `openfda.generic_name`** (query by either); **RxNav is RxNorm-native**. **DDInter and Beers/ACB are keyed by drug name/ingredient/ATC, NOT RxCUI** — bridge via RxNav (drug → ingredient RxCUI + name + ATC class), then match by name/ATC. That last hop is a string/class match with miss risk (salts, synonyms, combos) → needs a fallback and manual verification for demo drugs. **Every patient med must resolve to RxNorm or it's invisible to the knowledge layer — flag unresolved drugs, don't drop silently.**

**Real-world framing:** drug knowledge is easy/public; patient-data access is the genuinely hard real-world part (institutional integration) — which is exactly what the connector layer + "sit with IT, write a read-only connector mapping their DB to our FHIR schema" story addresses. Mirrors hub-and-spoke vendors (Redox, 1upHealth, Mirth).

---

## 7. Provider abstraction

`abc.ABC` (we own all impls, want shared helpers + runtime enforcement). Registry-dict factory.

```python
# providers/base.py
import abc, enum, asyncio
from dataclasses import dataclass, field
from datetime import datetime
from fhir.resources.R4B.bundle import Bundle

class Capability(enum.Flag):
    PATIENT=enum.auto(); MEDICATIONS=enum.auto(); CONDITIONS=enum.auto()
    ALLERGIES=enum.auto(); OBSERVATIONS=enum.auto(); PROCEDURES=enum.auto()

@dataclass
class Provenance:
    resource_ref: str            # "MedicationStatement/m1"
    source_provider: str         # "postgres:stmary"
    source_record_id: str | None = None
    span: dict | None = None     # PDF: {page,char_start,char_end,snippet}

@dataclass
class FetchResult:
    bundle: Bundle; source: str; fetched_at: datetime
    source_version: str | None = None
    partial: bool = False
    warnings: list[str] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)   # which resource types this source supports/returned (§15)

@dataclass
class HealthStatus: ok: bool; latency_ms: float; detail: str | None = None

class Provider(abc.ABC):
    id: str; capabilities: Capability
    @abc.abstractmethod
    async def fetch_patient(self, patient_id: str) -> FetchResult: ...
    @abc.abstractmethod
    async def health_check(self) -> HealthStatus: ...
    def supports(self, cap: Capability) -> bool: return cap in self.capabilities
    async def _timed(self, coro, *, timeout_s: float = 8.0):
        return await asyncio.wait_for(coro, timeout=timeout_s)

# providers/registry.py
_REGISTRY: dict[str, type[Provider]] = {}
def register(kind):                       # decorator
    def d(cls): _REGISTRY[kind]=cls; return cls
    return d
def build_provider(kind, **cfg): return _REGISTRY[kind](**cfg)
```

**Cross-cutting rules:** per-resource-type timeout via `_timed`; partial data returns what it could with `partial=True` + warning (never zero the bundle); normalize source errors into `ConnectorError` hierarchy; `health_check()` never raises; `coverage` records which resource types the source *supports* vs *returned* (drives §15 missing-data logic).

---

## 8. Connectors

**Mapping approach (decided):** explicit per-connector Python mapper functions (debuggable, no DSL framework). Generality proven by shipping **two different institution Postgres schemas** through the same `PostgresProvider`, not a generic engine.

| Connector | Status | Build notes |
|---|---|---|
| **MockFHIRProvider** | REAL — build first | `fhirpy` → `https://hapi.fhir.org/baseR4`; near-passthrough; project to subset + re-validate. Cache local snapshot so the demo never depends on the public server. Validates the subset early. |
| **PostgresProvider** | REAL — flagship | SQLAlchemy 2.x Core + asyncpg, **read-only role** + `SET TRANSACTION READ ONLY`. Two seeded institution DBs, deliberately different schemas; explicit mapper per institution → same provider, two configs proves generality. |
| **PDFProvider** | REAL on one frozen file | `pdfplumber` → `langextract`+Gemini (strict schema) → FHIR; persist char-offsets into `Provenance.span`. Text-layer PDF only (no OCR). Validate the demo PDF extraction once and freeze. |
| **HL7v2Provider** | HONEST SCAFFOLD | `hl7apy` parse one ADT → `Patient` demographics (+AL1→AllergyIntolerance if cheap). Framed openly as "scaffolded; full coverage via HL7 v2-to-FHIR IG / LinuxForHealth is roadmap." |

**Conditional scope (hour-6 gate, §22):** target 3 real + 1 scaffold. If the vertical slice isn't green by hour 6, fall back to 2 real (Mock FHIR + Postgres) + 2 scaffold; cut order **HL7v2 → PDF → Postgres**.

---

## 9. Cache layer (Postgres)

Hybrid: one row per FHIR resource, body in JSONB. Synchronous refresh-on-read guarded by an advisory lock. Provenance as plain columns. **No pgvector.**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE cached_resource (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    fhir_id TEXT NOT NULL,
    resource JSONB NOT NULL,
    source_provider TEXT NOT NULL,
    source_record_id TEXT,
    source_span JSONB,                 -- PDF page/char offsets for highlight
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_cached_resource UNIQUE (source_provider, resource_type, fhir_id)
);
CREATE INDEX idx_cr_patient_type ON cached_resource (patient_id, resource_type);
CREATE INDEX idx_cr_expires ON cached_resource (expires_at);
CREATE INDEX idx_cr_resource_gin ON cached_resource USING gin (resource jsonb_path_ops);

CREATE TABLE evidence_card (           -- external knowledge snippets, citable by id
    id TEXT PRIMARY KEY,               -- "openFDA:label:amitriptyline:adverse_reactions"
    source TEXT NOT NULL,              -- openFDA | DDInter | Beers | ACB | RxNav
    ref_url TEXT,
    snippet TEXT NOT NULL,
    query_used TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    action TEXT NOT NULL,              -- 'read'
    patient_id TEXT NOT NULL,
    source TEXT NOT NULL,
    resource_refs JSONB,
    actor TEXT
);
```

**Refresh-on-read:** `expires_at = fetched_at + TTL`; on read, if `min(expires_at) <= now()` grab `pg_try_advisory_xact_lock(hashtext(patient_id))` — winner re-pulls from the connector, upserts, writes audit; others serve cache. Set `X-Cache: HIT|REFRESH`. Upsert via `postgresql.insert(...).on_conflict_do_update(...excluded...)`. `async_sessionmaker(expire_on_commit=False)`. JSONB ↔ plain dicts.

---

## 10. Flattener (FHIR → LLM context)

Deterministic, template-based — **never feed raw FHIR JSON to the LLM**. Every line tagged `[ResourceType/id]`. Always render every category with explicit status (never silently omit — §15).

```markdown
# Patient [Patient/123] — 82yo Female
## Active Medications (8)
- Amitriptyline 25 mg PO HS — since 2026-02-10 [MedicationStatement/m2]
...
## Recent Labs / Vitals / Symptoms
- Reports dizziness, 2026-05-22 [Observation/o4]
## Allergies
- NOT DOCUMENTED — no source queried reports allergy data
```

---

## 11. Reasoning core — structured context + deterministic joins (NO vector DB)

**Principle:** the LLM is never a source of facts; it only proposes *links* between facts already fetched. Every fact comes from a patient FHIR resource or an external knowledge record we retrieved by exact key. **We do not use a vector database** — semantic similarity is fuzzy/unverifiable; our data is small enough to pass whole, and the knowledge joins are exact key lookups.

**Why no vector DB:** (1) one patient fits entirely in context → no retrieval, no recall-miss risk; (2) drug-knowledge joins are exact (RxCUI → openFDA/DDInter/Beers), not similarity — a vector match would be guessing where an exact join is a fact; (3) verifiability — citations are yes/no membership checks, not scores.

**Pipeline:**
1. **Assemble context** — pull patient FHIR from cache → flatten to tagged markdown → whole block into the prompt.
2. **Normalize** — each med name → RxCUI (+ ingredient RxCUI + ATC) via RxNav.
3. **Gather evidence (deterministic tool calls, replaces vector search)** — per drug: openFDA reactions + label; per drug pair: DDInter record; per drug: Beers/STOPP + ACB. Each returns an **evidence card** with an id (persisted to `evidence_card`).
4. **One reasoning call** — feed Gemini the flattened context + evidence cards; instruct it to propose hypotheses cross-referencing symptoms↔drugs/interactions/conditions/procedures present in context, citing `[ResourceType/id]` tags + evidence-card ids. Structured JSON output.
5. **Verify (deterministic, §13)** — drop any hypothesis whose citations don't resolve; assign confidence tier.
6. **Return** surviving cited, tiered hypotheses.

**Evidence sources (v1 priority):** (1) openFDA single-drug (hour-6 must-have); (2) DDInter interaction pairs (headline); (3) Beers/STOPP geriatric rules; (4) ACB burden (nice-to-have).

**One fuzzy seam, handled deterministically:** patient symptom text ("dizziness") ↔ MedDRA reaction term (`VERTIGO`) — curated synonym/string match against the FAERS terms openFDA actually returned, gated by the verifier. Optional tiny embedding *suggestion* allowed but must pass verification; never the source of truth, never a vector DB in the loop.

**Performance:** cold ≈10–20s (dominated by the single LLM call; everything else parallelizes); warm/cached sub-second to ~8s. Pre-warm the cache for the demo.

---

## 12. Cross-reference relationship taxonomy

The engine produces a *differential* — competing explanations for a finding — across entity types. Citation strength varies by relationship; tier and label accordingly.

| Relationship | Grounded by | Strength |
|---|---|---|
| Drug → symptom (adverse event) | openFDA FAERS + label | **Strong** (DB-cited) |
| Drug ↔ Drug (interaction) | DDInter + openFDA label | **Strong** (DB-cited) |
| Drug ↔ disease/condition | Beers drug-disease, STOPP, openFDA contraindications | Medium (guideline/label) |
| Drug ↔ age (geriatric) | Beers/STOPP/ACB | **Strong** (guideline) |
| Allergy ↔ Drug | logic match (allergy substance vs med list) | **Strong** (rule + cites both) |
| Lab ↔ Drug (e.g. low eGFR + renally-cleared drug) | openFDA renal/geriatric label + Beers | Medium |
| **Condition/disease → symptom** | LLM clinical reasoning + patient's cited `Condition` | **Weaker** — cites that it exists; link is reasoning |
| **Procedure/surgery → symptom** | LLM reasoning + temporal correlation from `Procedure` + dates | **Weaker** — same caveat |

**Extended confidence-tier ladder:** `supported_by_label` > `faers_signal` > `guideline (Beers/DDInter)` > `allergy/lab rule` > `patient-record clinical reasoning` > `speculative`. The condition/procedure→symptom links land in the lower tiers and are labeled "clinical reasoning — verify." Never present an LLM-reasoned link with the authority of an openFDA-cited one. Don't database-ground condition/procedure links (SNOMED graphs = too heavy for 24h); anchor them to the patient's cited resources and tier them low.

---

## 13. Grounding & anti-hallucination

You cannot make an LLM never hallucinate; you architect so anything hallucinated is **caught and dropped by deterministic code before the UI**. The guarantee is structural.

1. **Closed-world input** — the model only sees the flattened context + retrieved evidence cards; instructed to reference only entities present.
2. **Deterministic retrieval** — knowledge is fetched by code keyed on RxNorm; the model never recalls interaction facts.
3. **Mandatory citation schema** — structured output forces `patient_evidence: [ResourceType/id]` + `external_evidence: [{source, ref}]`; can't return a hypothesis without them.
4. **Post-generation verifier (plain Python, the actual guarantee)** — for each hypothesis: every `patient_evidence` id must exist in cache; every `external_evidence` ref must be a card actually fetched; PDF quotes must appear in source text (substring vs stored offsets); drug links must have the cited card *support* the claim (e.g. openFDA actually lists that reaction). **Fail → drop the hypothesis.**
5. **Values from the record, not prose** — doses, labs, dates, ages rendered from the FHIR resource by id; temporal claims computed from `effectiveDateTime`. Kills "40mg→400mg" errors.
6. **Confidence tier from source, not self-report** (§12 ladder); pure-`speculative` is dropped or loudly flagged.
7. **Abstention** — zero surviving hypotheses → "no well-supported explanation found," never invent.
8. **Human-in-the-loop is the last layer** — clinician confirms/dismisses; nothing is an action.

Honest scope: this guarantees **no fabricated facts/citations reach the UI** — not that every hypothesis is clinically correct (residual = why the clinician decides, and why condition/procedure links are tiered lower).

```json
{
  "hypothesis": "New dizziness may be associated with amitriptyline started 2026-02-10.",
  "patient_evidence": ["MedicationStatement/m2","Observation/o4"],
  "external_evidence": [
    {"source":"openFDA","ref":"openFDA:label:amitriptyline:adverse_reactions"},
    {"source":"Beers2023","ref":"Beers:anticholinergic"}
  ],
  "confidence_tier": "supported_by_label",
  "severity": "moderate"
}
```

---

## 14. Citations & linking

**A citation is a foreign key, not a search.** Every fact is assigned a stable id at ingest/fetch time; clicking a citation resolves the id by exact lookup (Postgres PK for patient data, `evidence_card` row for knowledge). No vector DB needed — you always have the id because you created it.

**Two citation classes prove two different things, and a hypothesis carries both:**
- **Patient-fact citations → link INTO the source document.** "He's on amitriptyline / reports dizziness." Click → jump to the exact spot: PDF page with the span highlighted (via `source_span` offsets), or the chart row if Postgres-sourced. Proves *"the patient actually has this."*
- **Knowledge citations → link OUT to medical knowledge.** "Dizziness is a reported reaction / Beers-inappropriate in elderly." Click → show the openFDA/Beers snippet + deep link. Proves *"the connection is real medicine, not invented."*

**Hypothesis card layout:**
> ⚠ **New dizziness may be associated with amitriptyline** (started 6 days ago)
> *Why surfaced:* amitriptyline is strongly anticholinergic; dizziness is a commonly reported reaction; anticholinergics are flagged inappropriate ≥65 (patient is 82); symptom began after the drug started.
> **From this patient's chart:** `[Amitriptyline 25mg — PDF p.2]` `[Dizziness — PDF p.4]`
> **Medical basis:** `[openFDA label: adverse reactions]` `[Beers 2023: anticholinergics]`

Chart citations answer "is this real for *him*?"; knowledge citations answer "is this real in *medicine*?"; the hypothesis is the bridge and the *why* line explains it. If a patient fact appears in multiple sources, link to the provenance the cache recorded (prefer the PDF for the demo highlight moment).

**Resolution endpoints:**
- `GET /patients/{id}/resource/{resource_type}/{fhir_id}` → cached FHIR resource (+ `source_span` if from PDF) → UI highlights.
- `GET /evidence/{card_id}` → snippet + ref_url → side panel.

**API citation payload** ships per hypothesis: `[{kind: "patient"|"openFDA"|"DDInter"|"Beers"|"ACB", ref, label, url?, snippet?}]`.

---

## 15. Missing-data handling

**Absence of documentation = "unknown," never "none."** Three states: present, explicitly-asserted-absent, not-documented.

- **FHIR mechanisms:** missing `AllergyIntolerance` = unknown; "no known allergies" is a *positive assertion* (SNOMED `716186003` or `List.emptyReason=nilknown`) emitted only when a source says so. `Observation.dataAbsentReason` for missing values.
- **Capability vs empty:** distinguish "connector doesn't support allergies" (no AL1 segments) from "supports and returned zero" — via `FetchResult.coverage`.
- **Flattener:** always render the category with explicit status (`NOT DOCUMENTED — source X has no allergy fields` vs `No known allergies (asserted by X)`); never silently omit.
- **Reasoning rules:** (1) never assert safety from absence; (2) downgrade confidence of any hypothesis depending on a missing field; (3) emit the gap as an explicit "data gap / unknowns" item recommending clinician confirmation.
- **UI:** per-category completeness indicator; gaps become clinician action items.

This is a scored asset — directly the "safety guardrails designed in" requirement, and the answer to "what happens when the chart is incomplete?"

---

## 16. Minimum viable input contract

The tool degrades gracefully. Tiers:

- **Tier 0 (floor to produce any cited hypothesis):** ≥1 medication (name resolvable to RxNorm) + ≥1 current symptom/finding. Enables openFDA single-drug attribution.
- **Tier 1 (floor for the actual "aha"):** ≥2 medications (interactions possible) + patient age (Beers/ACB) + ≥1 symptom + ideally med start dates (the temporal "started last week" hook).
- **Tier 2 (enrichment):** conditions, labs/renal function, allergies, dosages, procedures — raise quality, cut false positives, not required.

**Hard requirement:** every medication must resolve to RxNorm (the join key for all knowledge). Unresolved drugs are flagged, not dropped. Below Tier 1 the packet must say so ("limited input — low confidence"). One-line rule: *resolvable med + ≥1 symptom* to function; *≥2 dated meds + age + symptom* to be valuable.

---

## 17. API layer (FastAPI + OpenAPI)

Expose **slim Pydantic DTOs, not raw FHIR** (raw FHIR blows up TS codegen). Set `FastAPI(separate_input_output_schemas=False)`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/patients` | list demo patients (id, age, source; no name in reasoning context) |
| `GET` | `/patients/{id}/packet` | decision packet: summary + cited hypotheses; `X-Cache` header |
| `POST` | `/patients/{id}/refresh` | force connector re-pull (demo button) |
| `GET` | `/patients/{id}/resource/{rtype}/{fhir_id}` | resolve a patient citation (+span) |
| `GET` | `/evidence/{card_id}` | resolve a knowledge citation |
| `GET` | `/connectors` | registered providers + health + capabilities |
| `POST` | `/intake` | patient intake submission → seeds a source |
| `POST` | `/hypotheses/{id}/confirm` | clinician confirm (audited) |
| `POST` | `/hypotheses/{id}/dismiss` | clinician dismiss (audited; suppress similar) |
| `GET` | `/audit` | AuditEvent log |

DTOs: `Citation{source, ref, kind, url?, snippet?}`, `Hypothesis{id, text, why, patient_evidence[], external_evidence[Citation], confidence_tier, severity}`, `DecisionPacket{patient_id, summary_markdown, hypotheses[], data_gaps[], cache{}}`. **Auth:** `HTTPBearer` dev token (renders Swagger Authorize; subject → audit actor). **CORS:** allow `localhost:3000`.

---

## 18. Frontend integration

Codegen: `openapi-typescript http://localhost:8000/openapi.json -o ./src/lib/api/schema.d.ts` (npm `gen:api`). Client = `openapi-fetch` + `openapi-react-query`; one global auth middleware sets the bearer. Usage: `$api.useQuery("get","/patients/{id}/packet",{params:{path:{id}}})`; `$api.useMutation("post","/hypotheses/{id}/confirm")`. The typed client is a convenience — if codegen chokes on a schema, hand-write the fetch and move on.

---

## 19. Repo structure

```
polypharm/
├── backend/app/
│   ├── main.py                 # FastAPI, CORS, auth, routers
│   ├── api/                    # patients, connectors, intake, audit, hypotheses, evidence
│   ├── providers/              # base.py, registry.py, mock_fhir.py, postgres.py(+mappers/), pdf.py, hl7v2.py
│   ├── fhir/                   # subset.py (builders/validate), flatten.py
│   ├── cache/                  # models.py, repo.py (refresh-on-read, upsert, advisory lock)
│   ├── reasoning/              # core.py, verifier.py, prompts.py, knowledge/{openfda,ddinter,rxnav,beers,acb}.py
│   └── dtos.py
│   ├── seeds/                  # institution_a.sql, institution_b.sql, demo PDF, FHIR bundle, beers.json, ddinter.csv, acb.json
│   └── tests/                  # detector test (known true + known clean), flatten test, verifier test
├── frontend/src/
│   ├── app/(provider/, intake/)
│   └── lib/api/                # generated schema.d.ts + client.ts
├── docker-compose.yml          # postgres: app + institution_a + institution_b
└── .env.example
```

---

## 20. Security / PHI posture

- **Read-only connectors:** SELECT-only role + `SET TRANSACTION READ ONLY`; no write methods on the interface.
- **Minimization:** key on MRN, derive age from DOB, never pull name/address/phone/next-of-kin into reasoning (§5).
- **Transient cache:** institution is system of record; rows carry TTL + provenance; framed session-scoped.
- **Audit:** every connector read writes an `audit_event` row → projects to FHIR AuditEvent.
- **Synthetic data only:** no real PHI anywhere; Gemini calls carry no identifiers; no training on inputs.
- **Talking points (not built):** PHIPA/PIPEDA (Canada), SOC 2 Type II (Dialogue's bar), Canadian FHIR Baseline / CA Core+.

---

## 21. Performance budget (one patient)

| Phase | Cold | Warm |
|---|---|---|
| Connector fetch (parallel) | 1–3s | skipped |
| PDF source (langextract+Gemini) | +3–8s | skipped |
| RxNav normalize (parallel) | 0.5–1s | cacheable |
| openFDA lookups (parallel) | 1–2s | cacheable |
| DDInter/Beers/ACB (local) | <50ms | <50ms |
| Flatten | <50ms | <50ms |
| **Gemini reasoning (dominant)** | 4–8s | 4–8s |
| Verify | <50ms | <50ms |
| **Total** | **≈10–20s** | **sub-second–8s** |

Pre-warm the cache for the demo; optionally run one live ~10–15s "gathering" pass as the refresh flourish.

---

## 22. Hour-6 vertical-slice gate

By **hour 6**, this thread runs end-to-end or connectors get cut (HL7v2 → PDF → Postgres):
```
MockFHIRProvider.fetch_patient(hero) → FHIR subset Bundle → cache upsert
  → flatten (tagged) → reasoning (openFDA single-drug) → ≥1 verified cited hypothesis
  → GET /patients/{id}/packet → rendered in provider app with a clickable citation
```
After hour 6, widen the spine (Postgres, DDInter pairs, second app, PDF, polish). Not green → stop adding connectors, harden the slice.

---

## 23. Build order

1. FHIR subset builders + validate one instance of all 6 (kills the R4B import gotcha early).
2. Flattener against a hand-written bundle.
3. MockFHIRProvider + cache table + refresh-on-read.
4. Reasoning core v0: openFDA single-drug → cited hypothesis + verifier (**hour-6 slice**).
5. API `/packet` + `/resource` + provider app rendering one citation that resolves.
6. RxNav normalize + DDInter pairs → interaction hypotheses.
7. PostgresProvider + two institution seeds/mappers.
8. Patient intake app + `/intake`.
9. Beers/STOPP rules; PDF connector on frozen file (span highlighting).
10. ACB; HL7v2 scaffold; AuditEvent UI; missing-data UI; polish.

---

## 24. Config / env

```
GEMINI_API_KEY=...
OPENFDA_API_KEY=...           # free: open.fda.gov/apis/authentication
DEV_TOKEN=dev-secret
APP_DB_DSN=postgresql+asyncpg://app:app@localhost:5432/polypharm
INST_A_DSN=postgresql+asyncpg://ro:ro@localhost:5433/institution_a   # read-only role
INST_B_DSN=postgresql+asyncpg://ro:ro@localhost:5434/institution_b
CACHE_TTL_SECONDS=30
```
Vendor into `seeds/`: DDInter CSV (ddinter.scbdd.com), ACB list (GitHub `juliasbrain/acb_score_calculator`), transcribed Beers/STOPP JSON, one Synthea R4 bundle, one clinical PDF.

---

## 25. Development workflow — building with GSD (Get Shit Done)

**What it is:** GSD ([gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done/)) — a spec-driven, context-engineering meta-prompting workflow **for Claude Code** (Plan → Execute → Verify, ~29 slash-command skills, subagent orchestration) that keeps an AI coding agent on-spec across a long build without context rot. **Dev-time accelerator, NOT a runtime component.**

**Why it fits:** this PRD *is* the spec GSD consumes; the system decomposes into focused components (its sweet spot); a 24h multi-person build is where context rot hurts most.

| GSD phase | Our artifact |
|---|---|
| Plan | Feed this `PRD.md` → requirements + component breakdown; reconcile with §23. |
| Execute | Build component-by-component in §23 order; §22 hour-6 slice = first gate. |
| Verify | Validate against spec — the §13 verifier + `tests/` are the verification artifacts. |

**Adoption rule:** only use GSD if someone already knows it **or** it's set up **before** the 24h clock starts; otherwise the learning curve costs more than it saves — fall back to the §23 build order, which stands alone.
