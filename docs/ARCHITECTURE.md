# Architecture

MedFlow turns a heterogeneous patient record into a set of **cited, verifier-gated
hypotheses** about polypharmacy risk. The design is organized so that a single
deterministic invariant holds end to end: *nothing reaches the clinician unless it
carries a citation that resolves to a real, cached source.*

## Pipeline

```
connectors → FHIR R4B subset → Postgres cache (+audit) → tagged flattening
          → Gemini reasoning (+ knowledge evidence) → deterministic verifier
          → DecisionPacket API → clinician UI
```

### 1. Connectors (`backend/app/providers/`)

A read-only provider contract, `Provider(abc.ABC)` + `Capability` flags +
`FetchResult` / `Provenance` / `HealthStatus` dataclasses + a registry-dict factory.
Every connector implements the same interface and is reachable through `POST /intake`:

- **`MockFHIRProvider`**: fetches from a public HAPI FHIR `baseR4` server, projects to
  the subset, re-validates, and caches a local snapshot so the demo never depends on the
  live server.
- **`PostgresProvider`**: reads two deliberately-different institution schemas (A and B)
  through explicit per-institution mapper functions that produce identical FHIR. Proves
  the integration story generalizes across schemas.
- **`PDFProvider`**: extracts a frozen text-layer clinical PDF with `pdfplumber`,
  persisting char-offset spans into `Provenance.span` so a citation can deep-link to the
  exact quote.
- **`HL7v2Provider`**: a scaffold that parses one ADT message into `Patient`
  demographics (self-advertised as partial).

Partial fetches return what they could with `partial=True` + warnings (never a zeroed
bundle); source errors normalize to a `ConnectorError` hierarchy that the API maps to a
clean `502`.

> See [CONNECTORS.md](CONNECTORS.md) for the schema-agnostic connector contract,
> the per-institution Postgres mappers, char-offset provenance spans, and how to add
> a new source type.

### 2. FHIR R4B subset + flattener (`backend/app/fhir/`)

Every connector validates its output to a 6-resource R4B subset (Patient,
MedicationStatement, Condition, Observation, AllergyIntolerance, Procedure) via
`fhir.resources.R4B` at the boundary. A deterministic template **flattener** renders
that subset to markdown where **every line is tagged `[ResourceType/id]`**, and always
renders every clinical category with an explicit status (an absent category reads as
*unknown*, never *none*). Raw FHIR JSON is never fed to the model, the tags are exactly
what make the downstream citation checks decidable.

### 3. Postgres cache + audit (`backend/app/cache/`)

- `cached_resource`: a JSONB store, one row per FHIR resource, with idempotent upsert.
- TTL **refresh-on-read**: an advisory-lock winner re-pulls and upserts while others
  serve cache; the response sets `X-Cache: HIT | REFRESH | MISS`.
- `audit_event`: a row written on **every** read (resource, evidence, packet) and on
  intake, attributed to the authenticated token subject.
- `evidence_card`: persists external knowledge snippets, each citable by a stable id.

### 4. Knowledge layer (`backend/app/knowledge/`)

Each medication is normalized and enriched, then turned into citable **evidence cards**:

- **RxNav (NLM)**: normalize each medication to RxCUI (+ ingredient RxCUI + ATC);
  medications that don't resolve are flagged, never silently dropped.
- **openFDA**: single-drug adverse-reaction (FAERS) + label lookup keyed by
  RxCUI / generic name, with response caching and recorded fixtures so CI never calls
  the live API.
- **DDInter**: drug-pair interaction lookup, bridged from RxNorm via RxNav.
- **AGS Beers 2023**: geriatric potentially-inappropriate-medication rules.
- **ACB**: anticholinergic cognitive burden scoring.

The layer degrades gracefully: if an external key is missing or a service is down, it
returns fewer cards rather than failing the request.

### 5. Reasoning core + verifier (`backend/app/reasoning/`)

A single **Gemini** call consumes the flattened closed-world context plus the evidence
cards and returns structured JSON hypotheses that cite `[ResourceType/id]` tags and
evidence-card ids. Then two **model-free** gates run:

- `verify_citations` drops any hypothesis whose patient citation tag isn't present in the
  flattened text, whose evidence ref isn't a fetched card id, or whose `kind` is unknown
  (one bad citation taints the whole hypothesis).
- `verify_packet` re-checks every surviving citation against the live cache and enforces
  PDF-quote integrity (`page_text[start:end] == span.snippet`).

Confidence tiers are assigned from the *source*, never self-reported. When zero
hypotheses survive, the packet abstains ("no well-supported explanation found") rather
than inventing one. Below a data threshold, a minimum-input contract flags the result as low
confidence and emits explicit data-gap items (absence is *unknown*, never
*safe*).

> See [CAPABILITIES.md](CAPABILITIES.md) for the full reasoning pipeline, the two
> citation gates, deterministic confidence-tier derivation, and the knowledge-evidence
> and audit-trail details.

### 6. API + UI (`backend/app/api/`, `frontend/`)

The FastAPI surface exposes slim Pydantic DTOs (`Citation`, `Hypothesis`,
`DecisionPacket`, …) in an OpenAPI 3.1 schema (`separate_input_output_schemas=False`).
A committed contract drift-guard test asserts the published schema matches the live app.
The Next.js UI generates its typed client from that contract (`openapi-fetch` +
`openapi-react-query` with a global bearer middleware) and renders hypothesis cards whose
citation chips resolve patient facts (with PDF span highlighting) and knowledge snippets.

## Security posture

- Read-only institution access: a `SELECT`-only role plus `SET TRANSACTION READ ONLY`;
  no connector exposes a write path.
- Data minimization on the reasoning + citation-read paths: keyed on MRN, age derived
  from DOB; name / address / phone / next-of-kin never enter the reasoning context.
- Bearer `DEV_TOKEN` auth gates write/decision endpoints; the token subject is the audit
  actor. Synthetic data only; no secrets committed.

## Testing & CI

The backend holds a **100% statement-coverage gate** on the correctness-critical core
(`fhir/`, `providers/`, `cache/`, `knowledge/`, `reasoning/`); API/DTO wiring is covered
but ungated. Knowledge tests run against recorded fixtures (no live API in CI). The
frontend runs lint + strict `tsc` + a `vitest` suite + a production `next build`. CI runs
both on every PR.
