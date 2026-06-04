# MedFlow

**Polypharmacy decision support that never fabricates.** MedFlow ingests a patient's
record from heterogeneous medical-institution sources, normalizes everything into a
unified FHIR R4 subset, and runs a reasoning core that surfaces **cited, tiered
hypotheses** about the patient's medications, interactions, conditions, and symptoms.

> **Core guarantee:** every clinical claim surfaced to the clinician carries a
> **resolvable citation** to a real source, and a **deterministic verifier** drops any
> hypothesis whose citations don't resolve. Nothing fabricated reaches the UI. The
> system gathers and connects evidence; the clinician decides.

⚠️ Research / demonstration software on **synthetic data only**, **not a medical
device** and **not for clinical use**. See [DISCLAIMER.md](DISCLAIMER.md).

---

## Highlights

- **Schema-agnostic connectors over any database.** One `PostgresProvider` class
  normalizes two deliberately-divergent institution schemas (a normalized one-table-per-resource
  schema and a flat legacy single-table one) into the *same* FHIR R4B subset, selected by
  a constructor argument. Adding a source is a small, registered provider.
- **Cited, verifier-gated reasoning that cannot fabricate.** Every surfaced hypothesis must
  cite `[ResourceType/id]` patient tags or evidence-card ids; a deterministic, no-model
  **verifier re-checks every citation against the cache** and drops any hypothesis whose
  citations don't resolve. If nothing survives, the packet abstains.
- **Multi-source ingestion.** Five registered connectors across four classes: a mock FHIR
  server, a clinical PDF, an HL7v2 ADT message, and two Postgres institutions, each
  validating to a 6-resource FHIR R4B subset at its boundary.
- **Char-offset provenance for documents.** PDF citations carry a page plus exact
  `start`/`end` offsets and the verbatim snippet, with a `page_text[start:end] == snippet`
  invariant the verifier can re-check before a quote is trusted.
- **Five drug-safety knowledge sources.** RxNav (RxNorm resolution), openFDA (adverse
  events + labels), DDInter (drug-drug interactions), Beers (AGS 2023 potentially-inappropriate
  medications, age-gated ≥65), and ACB (anticholinergic cognitive burden) supply the
  citable evidence cards.
- **Honest about absence.** Coverage is computed per advertised capability, audit events are
  written on every read, and safety-critical data gaps downgrade hypothesis confidence rather
  than asserting safety from absence.

## How it works

```
 connectors            normalize            cache              reason                verify              serve
┌───────────┐        ┌──────────┐       ┌──────────┐      ┌────────────┐       ┌─────────────┐      ┌──────────┐
│ mock-FHIR │        │ FHIR R4B │       │ Postgres │      │  Gemini    │       │deterministic│      │ FastAPI  │
│ Postgres  │  ───►  │  subset  │ ───►  │  cache   │ ───► │ reasoning  │ ───►  │  verifier   │ ───► │ /packet  │ ───► Next.js UI
│ PDF       │        │(validated│       │ + audit  │      │ over tagged│       │ (drops un-  │      │  + chips │
│ HL7v2     │        │ + spans) │       │ TTL      │      │ flattening │       │ resolvable) │      │          │
└───────────┘        └──────────┘       └──────────┘      └────────────┘       └─────────────┘      └──────────┘
                                                                ▲
                                              knowledge: RxNav · openFDA · DDInter · Beers · ACB
```

1. **Connectors** (a read-only provider registry) fetch a patient from a mock FHIR
   server, two deliberately-different institution Postgres schemas, a clinical PDF, or
   an HL7v2 ADT message. Each validates to a 6-resource **FHIR R4B subset** at its
   boundary and records char-offset provenance spans where the source is a document.
2. The record is **cached** in Postgres (JSONB, one row per resource) with TTL
   refresh-on-read and an **audit event written on every read**.
3. A deterministic **flattener** renders the cached record to markdown where *every
   line is tagged* `[ResourceType/id]`. Raw FHIR JSON is never sent to the model.
4. A single **Gemini reasoning** call consumes that tagged context plus knowledge
   **evidence cards** and returns structured hypotheses that cite `[ResourceType/id]`
   tags and evidence-card ids.
5. The **verifier** (no model involved) drops any hypothesis whose patient citation
   isn't in the cache, whose knowledge citation isn't a fetched card, or whose PDF
   quote doesn't appear verbatim in the source text. This is the anti-hallucination
   guarantee.
6. The surviving, cited hypotheses are served as a **`DecisionPacket`** and rendered as
   cards with clickable citation chips that resolve to the underlying source.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design and
[docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for the knowledge datasets and provenance.

## Repository layout

- **`backend/`**: FastAPI service holding the FHIR subset + flattener, the connector/provider
  registry, the Postgres cache + audit, the knowledge layer (RxNav / openFDA / DDInter /
  Beers / ACB), the reasoning core + verifier, and the typed API. Python 3.12.
- **`frontend/`**: Next.js 16 + TypeScript clinician UI (TanStack Query + a typed
  `openapi-fetch` client) that renders the decision packet and resolves citations.
- **`docker-compose.yml`**: Postgres services for the app database plus the two
  seeded institutions (`institution_a`, `institution_b`).
- **`docs/`**: architecture, data sources, and deployment guides.

## Quick start

**Prerequisites:** Python 3.12, Node 22, Docker (for the Postgres layer).

```bash
# 1. Configure environment
cp .env.example .env          # then set DEV_TOKEN; GOOGLE_GENAI_API_KEY / OPENFDA_API_KEY
                              # are optional (the reasoning + knowledge layers degrade
                              # gracefully without them).

# 2. Start the database layer (app DB + the two seeded institutions)
docker compose up -d

# 3. Backend
make backend-install
make backend-test                       # full suite + the core coverage gate
cd backend && uvicorn app.main:app --reload   # http://localhost:8000  (/docs for Swagger)

# 4. Frontend (in a second terminal)
cd frontend && npm install
npm run dev                             # http://localhost:3001
```

`make test` and `make lint` run both sides. The backend serves OpenAPI at `/docs`; the
frontend's typed client is generated from that contract via `npm run gen:api`.

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /patients/{id}/packet` | The `DecisionPacket`, cited hypotheses + data gaps + cache status (`X-Cache` header) |
| `GET /patients/{id}/resource/{type}/{fhir_id}` | Resolve a patient-fact citation (with `source_span` when PDF-sourced) |
| `GET /evidence/{card_id}` | Resolve a knowledge citation to its snippet + reference URL |
| `POST /patients/{id}/refresh` | Force a connector re-pull |
| `POST /intake` | Ingest a patient from a registered connector |
| `POST /hypotheses/{id}/confirm` \| `/dismiss` | Record an audited clinician decision |
| `GET /patients` · `GET /connectors` · `GET /audit` | Roster, live connector health + capabilities, audit log |

All write/decision endpoints require a bearer **`DEV_TOKEN`** (rendered in Swagger's
*Authorize*). The authenticated token's subject is recorded as the audit `actor`.

## Security & data posture

- **Synthetic data only.** No real PHI anywhere in the repo or the reasoning path.
- **Read-only institutions.** Postgres access uses a `SELECT`-only role plus
  `SET TRANSACTION READ ONLY`; no connector exposes a write method.
- **Data minimization.** Reasoning keys on MRN and derives age from DOB; name, address,
  phone, and next-of-kin are never pulled into the reasoning context.
- **No secrets in the repo.** `.env.example` holds `PLACEHOLDER`s; real values live only
  in a local, git-ignored `.env`.

## Scope & limitations

MedFlow is a focused, working demonstration of *cited, verifier-gated* clinical reasoning, not a complete product. Known boundaries, stated honestly:

- **HL7v2 connector is a scaffold**: it parses ADT PID demographics into a `Patient`
  and openly self-advertises as partial; `AL1`→`AllergyIntolerance` mapping is not yet
  implemented.
- **PDF extraction is deterministic** (`pdfplumber` text layer + frozen char-offset
  spans). There is no LLM-based extraction and no OCR for scanned/image-only PDFs.
- **Geriatric rules are Beers-only** (AGS 2023). STOPP/START criteria are not included.
- **The differential is model-driven.** The breadth of entity-pair reasoning
  (drug↔symptom, drug↔drug, drug↔age, …) emerges from the prompt and the knowledge
  sources; the *verifier* guarantees that whatever surfaces is cited and resolvable, but
  exhaustive pair coverage is not enforced.
- **Single-process cache.** Idempotent upsert + advisory-lock refresh are implemented;
  a production deployment would harden these for true multi-writer concurrency.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): components and data flow
- [docs/CONNECTORS.md](docs/CONNECTORS.md): the provider registry, the supported source types, and how to add a connector
- [docs/CAPABILITIES.md](docs/CAPABILITIES.md): the knowledge sources, the cache + audit model, and the citation/verifier guarantees
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md): knowledge datasets, licenses, provenance
- [docs/DEPLOY.md](docs/DEPLOY.md): container build + Google Cloud Run deployment
- [CONTRIBUTING.md](CONTRIBUTING.md): branching, PRs, and the test policy
- [DISCLAIMER.md](DISCLAIMER.md): safety and intended-use notice

## License

MedFlow is released under the **[Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International License (CC BY-NC-SA 4.0)](LICENSE)**. You are free to use, share, and build
on it, provided you **give credit to MedFlow as the source**, **don't use it for commercial
purposes** (i.e. to make money), and **license your own versions under these same terms**.
For a commercial arrangement, contact the copyright holder.
