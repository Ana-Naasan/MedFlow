# MedFlow Capabilities

MedFlow is polypharmacy decision support built around a single hard premise: **it never
fabricates a clinical claim.** It ingests a patient record from heterogeneous medical
sources (a mock FHIR server, two deliberately different institution Postgres schemas, a
clinical PDF, an HL7v2 ADT message), normalizes everything into a 6-resource FHIR R4B
subset, caches it with an audit event on every read, and runs a single Gemini reasoning
call over a tagged, PII-minimized flattening of that record plus drug-safety **evidence
cards** drawn from five knowledge sources. A **deterministic verifier** then re-checks
every citation against the actual cache and drops any hypothesis whose citations do not
resolve. What reaches the clinician is a `DecisionPacket` of **cited, tiered hypotheses**
about medications, interactions, conditions, and symptoms, rendered as cards with
clickable citation chips that resolve back to the underlying source. The system gathers
and connects evidence; the clinician decides.

> Research and demonstration software on **synthetic data only**. **Not a medical
> device** and **not for clinical use.** See [../DISCLAIMER.md](../DISCLAIMER.md).

---

## What makes it notable

The differentiator is not the model. It is everything wrapped around the model so that a
fallible generator cannot put an unsupported claim in front of a clinician. Three
properties hold end to end:

1. **No-fabrication guarantee.** Every clinical claim surfaced carries a *resolvable*
   citation, and a non-AI verifier drops the entire hypothesis on the first citation that
   does not resolve. Hypotheses are never surfaced with a partial citation set.
2. **Honest absence.** A missing data category is reported as *unknown*, never as *none*.
   Connectors mark coverage per advertised capability, the flattener distinguishes "stated
   as none by source" from "not documented", and gap-driven downgrades lower confidence
   rather than asserting safety from absence.
3. **Auditable reads.** Every cache read and every evidence read writes an immutable audit
   event, and clinician confirm/dismiss actions are audited too.

---

## The pipeline, end to end

```
 connectors          normalize           cache             reason               verify             serve
┌───────────┐      ┌──────────┐      ┌──────────┐     ┌────────────┐      ┌─────────────┐     ┌──────────┐
│ mock-FHIR │      │ FHIR R4B │      │ Postgres │     │  Gemini    │      │deterministic│     │ DecisionP│
│ Postgres  │ ───► │  subset  │ ───► │ JSONB    │ ──► │ over tagged│ ───► │  verifier   │ ──► │  acket   │ ──► UI chips
│ PDF       │      │(validated│      │ + audit  │     │ flattening │      │ (drops un-  │     │          │
│ HL7v2     │      │ + spans) │      │ TTL      │     │ + evidence │      │ resolvable) │     │          │
└───────────┘      └──────────┘      └──────────┘     └────────────┘      └─────────────┘     └──────────┘
                                                            ▲
                                       knowledge cards: RxNav · openFDA · DDInter · Beers · ACB
```

### 1. Connectors (read-only provider registry)

Connectors implement a common `Provider` contract
(`backend/app/providers/base.py:57`): `fetch_patient`, `health_check`, `supports`, and an
`aclose` for disposing pooled resources. A registry maps a name to a factory
(`backend/app/providers/registry.py`); registration happens at import time, and every
connector ships a seeded default source so the project runs standalone, with optional
kwargs overriding without changing the `/intake` contract
(`backend/app/providers/__init__.py:29`).

| Registry name | Class | Capabilities | Default seeded source |
|---|---|---|---|
| `mock-fhir` | `MockFHIRProvider` | all 6 | HAPI FHIR R4 server, snapshot-first from `seeds/mock_fhir_snapshot.json` |
| `pdf` | `PDFProvider` | Patient, Medications, Conditions | `seeds/sample_clinical.pdf` |
| `hl7v2` | `HL7v2Provider` | Patient only | `SAMPLE_ADT_A01` (an ADT^A01) |
| `institution-a` | `PostgresProvider(institution="a")` | all 6 | `INSTITUTION_A_DSN` (db `institution_a`) |
| `institution-b` | `PostgresProvider(institution="b")` | all 6 | `INSTITUTION_B_DSN` (db `institution_b`) |

A notable detail: **one connector class normalizes two deliberately divergent schemas.**
`PostgresProvider` (`backend/app/providers/postgres.py:509`) serves both `institution-a`
(a normalized, one-table-per-resource schema) and `institution-b` (a flat legacy single
`clinical_events` table discriminated by `event_class`), branching on the `institution`
constructor arg. The demo patient `DEMO-001` is seeded in both with the same clinical
profile so the two schemas produce the same FHIR subset bundle, the "same output"
guarantee. Document sources (PDF) additionally record **char-offset provenance spans**
where `page_text[start:end] == snippet` (`backend/app/providers/pdf.py`), which is what
later makes a PDF quote independently verifiable.

Live connector health and capabilities are auto-discovered and probed by
`/connectors`, which never echoes the internal `HealthStatus.detail` (it can carry a DSN
host/port) (`backend/app/providers/status.py`).

### 2. Normalize to a 6-resource FHIR R4B subset

The canonical subset is six R4B resource types: **Patient, Condition,
MedicationStatement, Observation, AllergyIntolerance, Procedure**. Each connector
normalizes source data into these types and emits a searchset bundle. At the `/intake`
boundary, `validate_fhir_resource` (`backend/app/fhir/validate.py:48`) re-validates each
fetched dict against the subset: in-subset-but-invalid resources are dropped as an honest
gap (not a 4xx), and out-of-subset types are silently filtered. Validation warnings
interpolate only the exception class name, never the raw pydantic error (which would echo
name/address/telecom), so no PII leaks into a warning.

### 3. Cache with an audit event on every read

The record is cached in Postgres as JSONB, **one row per FHIR resource**, keyed by
`(patient_id, resource_type, resource_id)` so a resource is never duplicated
(`backend/app/cache/models.py:19`). The cache is **TTL refresh-on-read**: `get_or_refresh`
serves fresh cache as a `HIT`, and on a stale or missing entry takes a Postgres
transaction-scoped advisory lock so concurrent readers do not stampede the source. The
winner re-pulls (`REFRESH`); lock-losers serve current cache (`HIT`); nothing
cached or fetched is a `MISS` (`backend/app/cache/repo.py`). That status is surfaced on the
`X-Cache` response header.

Every read path writes an **immutable audit event** (`event_type` `resource_read` or
`evidence_read`) recording the patient, the resource reference, the actor, and a
timestamp (`backend/app/cache/models.py:47`, `backend/app/cache/repo.py`). The bulk
`list_patient_resources` read used to assemble reasoning context excludes bookkeeping
rows and writes no audit event by design, so the audit log reflects citation-resolving
reads rather than internal sweeps.

### 4. Tagged flattening (raw FHIR JSON never reaches the model)

`flatten_to_tagged_text` (`backend/app/fhir/flatten.py:27`) renders the cached resources
to markdown where **every data line is prefixed with a `[ResourceType/id]` tag** (for
example `[MedicationStatement/ms-001]`). That tag is the exact token the citation gates
resolve against. Five clinical categories are rendered in fixed order (Medications,
Conditions, Labs and Symptoms, Allergies, Procedures), and every category is always shown,
even when empty, in one of three states:

- **present** -> the tagged, extracted values;
- **stated as none by source** -> for explicit "no known allergy" codes;
- **not documented** -> when a category has no items.

The Patient resource is PII-minimized before it ever enters reasoning context: a
fail-closed allow-list keeps only `resourceType`, `id`, and `gender`, derives `ageYears`
from DOB, and keeps an MRN-only identifier; non-Patient resources have `name`, `address`,
`telecom`, and `contact` recursively stripped (`backend/app/fhir/subset.py`). Raw FHIR
JSON is never sent to the model.

### 5. Gemini reasoning over tagged context plus evidence cards

A single reasoning call (`run_reasoning`, `backend/app/reasoning/core.py:455`) consumes
the tagged context plus the knowledge **evidence cards** and returns structured
hypotheses that cite `[ResourceType/id]` tags and evidence-card ids. The model is
`gemini-2.5-flash` (`core.py:38`), called via `google.genai` with
`response_mime_type="application/json"` and `temperature=0.0` for deterministic,
structured output. If the API key is unset, or the API errors (including 5xx
"model overloaded"), reasoning returns an empty list, a uniform abstention signal that
degrades to a static, always-servable scaffold rather than failing the request
(`backend/app/reasoning/pipeline.py`).

Before the deterministic verifier runs, `run_reasoning` already applies several
in-prompt-context gates so unsupported output is suppressed early:

- **In-prompt citation gate** (`verify_citations`, `core.py:359`): a hypothesis with no
  citations is dropped; a citation of an unknown kind taints the whole hypothesis; a
  `resource` citation must match a tag actually present in the flattened text (matched
  line-anchored so a `[Type/id]` substring inside source free text cannot forge a tag);
  an `evidence` citation must be in the known evidence-id set. Any unresolved citation
  drops the entire hypothesis.
- **Tier derivation** (`derive_confidence_tier`, `core.py:432`): confidence comes from the
  surviving citations, not the model's self-reported string (see tiers below).
- **Output-language gate** (`core.py:72`): a deterministic regex drops any hypothesis
  whose text asserts causal attribution ("caused by", "due to"), a drug directive
  ("discontinue", "should stop"), or a dose directive. It is curated to not fire on valid
  associational language (for example "increased risk" or "increase in INR").

### 6. The deterministic verifier (the anti-hallucination gate)

`verify_packet` (`backend/app/reasoning/verifier.py:54`) is plain synchronous code, **no
AI involved.** It is the authoritative gate: it re-checks every citation against the
*actual cache* rather than the prompt context. The rule is strict: **per hypothesis, all
citations must pass or the whole hypothesis is dropped.** `_check_hypothesis` returns on
the first failing citation, and only hypotheses with no drop reason are kept. The exact
checks (`verifier.py:202`):

| Citation kind | Check | Drop reason on failure |
|---|---|---|
| unknown | kind not in the resource or evidence sets | `Unknown citation kind ..., cannot verify` |
| resource | `ref` splits into a non-empty `ResourceType/id` | `Malformed resource ref ..., expected ResourceType/id` |
| resource | `resource_lookup(patient_id, type, id)` resolves in the cache | `Patient resource ... not found in cache` |
| evidence | `evidence_lookup(ref)` returns a card | `Evidence card ... not found` |
| evidence | the card carries a non-empty `snippet` | `Evidence card ... has no backing snippet` |
| evidence | if the card has a span and page text is supplied, `page_text[start:end]` equals `snippet` verbatim | `PDF quote mismatch ...` |

If every hypothesis is dropped, **the packet abstains**: it returns a `DecisionPacket` with
`summary_markdown` set to `"No well-supported explanation found."` and an empty hypothesis
list, while preserving `data_gaps`, `completeness`, and `cache_status`. For surviving
hypotheses, each resolvable resource citation gets its PDF `source_span` attached so the
frontend can render a clickable highlight; a resource with no span keeps a non-interactive
chip.

The PDF-quote integrity check is the strongest illustration of the no-fabrication
posture: a quoted span is dropped unless the claimed snippet is found *verbatim* at the
claimed character offsets in the source page text.

### 7. The `DecisionPacket` and the UI citation chips

The served `DecisionPacket` (`backend/app/dtos.py:52`) carries `patient_id`,
`summary_markdown`, the surviving `hypotheses`, `data_gaps`, per-category `completeness`,
and `cache_status`. Each `Hypothesis` (`dtos.py:40`) has `id`, `title`, `why`, `severity`,
`confidence`, an optional dismiss-similar `group`, and a list of `Citation`s. A `Citation`
(`dtos.py:24`) has a `kind`, a `ref`, an optional `label`, and an optional `source_span`
(1-based `page`, char `start`/`end`, and the exact `snippet`). The frontend renders each
hypothesis as a card with clickable citation chips that resolve through the API back to
the underlying patient resource (with the PDF highlight when present) or the evidence
card's snippet and reference URL.

---

## Cited, tiered hypotheses

Hypotheses span medications, drug-drug interactions, conditions, and symptoms (the same
categories the flattener surfaces). The breadth of entity-pair reasoning emerges from the
prompt and the knowledge sources; the verifier guarantees that whatever surfaces is cited
and resolvable. There is **no separate tier field**: the tier *is* the `confidence` string,
derived deterministically from the citations that survived verification
(`derive_confidence_tier`, `core.py:432`):

| Tier | Confidence | Condition |
|---|---|---|
| Tier 1 | `high` | at least one surviving `evidence` citation (a direct external-evidence link) |
| Tier 2 | `medium` | only `resource` citations (patient FHIR, uncorroborated) |
| Tier 3 | `low` | no surviving citations |

After verification, a **gap-driven downgrade** (`apply_gap_downgrades`,
`backend/app/fhir/data_gaps.py`) lowers confidence one rung when a safety-critical
category (AllergyIntolerance or Observation) is absent *and* the hypothesis cites a
MedicationStatement. The principle is "never claim safety from absence": an already-`low`
or unrecognized confidence is left unchanged.

---

## The five drug-safety knowledge sources (evidence cards)

Knowledge modules emit `EvidenceSnippet` atoms (`id`, `kind`, `ref`, `label`) with stable,
deterministic ids so a citation survives intact into the packet; the persisted form is an
`EvidenceCard` (`backend/app/cache/models.py:35`) keyed by that id. An evidence citation
resolves only if a real fetched-or-computed card with a non-empty snippet exists.

| Source | Provides | Provenance | Notes |
|---|---|---|---|
| **RxNav** (`knowledge/rxnav.py`) | free-text drug name -> RxNorm/RxCUI, ingredient, ATC, canonical name | NIH RxNav REST (`https://rxnav.nlm.nih.gov/REST`) | Bridges names before DDInter lookups. Transport errors never raise; `network_error` distinguishes "not found" from "API unavailable", and unmatched drugs are flagged, never silently dropped. |
| **openFDA** (`knowledge/openfda.py`) | adverse-event aggregates (FAERS) plus drug-label sections | `https://api.fda.gov/drug` | Async client with a token-bucket rate limiter, an in-process LRU cache (1-hour TTL), and a 429 retry. Query values are escaped to prevent Lucene/Elasticsearch injection. Optional `OPENFDA_API_KEY`. |
| **DDInter** (`knowledge/ddinter.py`, seed `ddinter.csv`) | drug-drug interaction pairs at `Minor`/`Moderate`/`Major` | DDInter 2.0 (`https://ddinter.scbdd.com`), free for academic and non-commercial use | Keyed by drug name; bridges RxNorm to DDInter names via a narrow vendored synonym map, marking synonym or approximate hits `unsure` rather than dropping them. |
| **Beers** (`knowledge/beers.py`, seed `beers.json`) | AGS 2023 Beers potentially-inappropriate-medication rules for adults >= 65 | 2023 AGS Beers Criteria Update, copyright American Geriatrics Society, reproduced for decision-support and educational use | Age-gated and honest about it: unknown age returns "UNKNOWN" (not "no risk"); age < 65 is an explicit empty result. No external API. |
| **ACB** (`knowledge/acb.py`, seed `acb.json`) | Anticholinergic Cognitive Burden score (per-drug 1/2/3 summed to a total) | Carnahan RM et al., *J Clin Pharmacol* 2006, reproduced for educational and decision-support use | No external API and no hard age gate; for adults >= 65 with a top score the snippet adds an elevated-cognitive-risk rider. |

The seed datasets and their licenses are detailed in
[DATA_SOURCES.md](DATA_SOURCES.md). All seeds are publicly downloadable reference datasets
or synthetic dev data: no real patient data is used.

---

## The audit trail

Audit is not opt-in. `write_audit_event` (`backend/app/cache/repo.py`) appends and flushes
immediately, and is called unconditionally on every read path: `get_or_refresh` and
`get_resource` write a `resource_read`, and `get_evidence_card` writes an `evidence_read`
with `resource_ref` of the form `evidence/{id}`. Clinician `hypothesis_confirmed` and
`hypothesis_dismissed` actions are also audited, idempotently (a no-op transition writes no
duplicate row). `list_audit_events` returns newest-first, capped at 50, so the endpoint
cannot stream the whole log. Audit events are immutable records: written, never updated.

Structured logging is JSON, one line per record, on a single idempotent `medflow` root
logger (`backend/app/observability/logging.py`). Partial fetches are surfaced as
non-blocking notices rather than silent gaps (`backend/app/observability/warnings.py`).

---

## Data posture and intended use

- **Synthetic data only.** No real PHI anywhere in the repo or the reasoning path. The
  demo PDF is a synthetic discharge summary; the sample FHIR bundle is Synthea synthetic
  data under Apache 2.0.
- **Read-only institutions.** Every Postgres query runs inside a
  `BEGIN READ ONLY` transaction (the enforced, test-pinned invariant), with a
  `SELECT`-only `umraa_reader` role as defense in depth. No connector exposes a write
  method (`backend/app/providers/postgres.py`).
- **Data minimization.** Reasoning keys on MRN and derives age from DOB; name, address,
  phone, and next-of-kin never enter the reasoning context.
- **Honest scope.** The HL7v2 connector is a self-advertised scaffold (PID demographics
  only); PDF extraction is deterministic with no OCR; geriatric rules are Beers-only.

**MedFlow is research and demonstration software. It is not a medical device and is not for
clinical use.** It is a working demonstration of cited, verifier-gated clinical reasoning,
not a complete product or a claim of clinical efficacy. See
[../DISCLAIMER.md](../DISCLAIMER.md).

## See also

- [ARCHITECTURE.md](ARCHITECTURE.md): components and data flow
- [DATA_SOURCES.md](DATA_SOURCES.md): knowledge datasets, licenses, provenance
- [../README.md](../README.md): quick start and API surface
