# Connectors

The interesting part of MedFlow is that *one* read-only connector class reads two
deliberately different hospital database schemas, no matter the shape, and normalizes
both into the exact same FHIR R4B subset. Every source (a mock FHIR server, two
Postgres institutions, a clinical PDF, an HL7v2 ADT message) hides behind a single
`Provider` interface, so the rest of the system never learns where a record came from.
Document sources additionally carry char-offset provenance spans so a citation can be
highlighted back in the original text.

> Research / demonstration software on **synthetic data only**. Not a medical device and
> not for clinical use.

---

## The `Provider` interface

Every connector is a `Provider` subclass (`backend/app/providers/base.py:57`). The
contract is small:

```python
class Provider(abc.ABC):
    id: str
    capabilities: Capability

    @abc.abstractmethod
    async def fetch_patient(self, patient_id: str) -> FetchResult: ...

    @abc.abstractmethod
    async def health_check(self) -> HealthStatus: ...

    def supports(self, cap: Capability) -> bool:        # cap in self.capabilities
        return cap in self.capabilities

    async def aclose(self) -> None:                     # default no-op
        return None
```

- **`Capability`** (`base.py:9-15`) is an `enum.Flag` with six members, in this exact
  declaration order: `PATIENT, MEDICATIONS, CONDITIONS, ALLERGIES, OBSERVATIONS,
  PROCEDURES`. A connector OR-combines the flags it advertises. The order matters: the
  `/connectors` status endpoint emits capability names in this order (`status.py:28-30`).
- **`fetch_patient`** returns a `FetchResult` (`base.py:26-35`) carrying the normalized
  `bundle`, the `source`, `fetched_at`, a `partial` flag, `warnings`, a list of
  `Provenance` (`base.py:18-23`), and a `coverage` map.
- **`health_check`** returns a `HealthStatus` (`base.py:38-42`): `ok`, `latency_ms`, and
  an optional internal-only `detail` (which can carry a DSN host/port, so it is never
  served).
- **`aclose`** is a no-op by default; a connector that opens a long-lived resource (a
  connection pool) overrides it so the `/connectors` prober can build a throwaway
  instance and dispose of it without leaking.

Failures use two exceptions (`base.py:45-54`): `ConnectorUnavailable` for an unreachable
source, `ConnectorDataError` for data that cannot be normalized. Both derive from
`ConnectorError`.

Every connector returns the same bundle shape, a FHIR searchset:

```json
{ "resourceType": "Bundle", "type": "searchset", "entry": [ { "resource": { ... } } ] }
```

### The registry

`providers/registry.py` is a name to factory dict:

- `register(name, factory)` (`registry.py:16`) adds a connector.
- `build(name, **kwargs) -> Provider` (`registry.py:20`) constructs one, raising
  `ConnectorNotFound` if the name is unknown.
- `list_connectors() -> list[str]` (`registry.py:27`) returns names in insertion order.

Registration happens at import time in `providers/__init__.py:29-46`. Each connector
ships a seeded default source so the project runs standalone, with optional `kwargs`
overriding the source without changing the `/intake` contract:

```python
register("mock-fhir", MockFHIRProvider)
register("pdf", lambda **kwargs: PDFProvider(kwargs.get("path") or _SEEDED_PDF))
register("hl7v2", lambda **kwargs: HL7v2Provider(kwargs.get("raw_message") or SAMPLE_ADT_A01))
register("institution-a", lambda **kwargs: PostgresProvider(
    dsn=kwargs.get("dsn") or INSTITUTION_A_DSN, institution="a", pool=kwargs.get("pool")))
register("institution-b", lambda **kwargs: PostgresProvider(
    dsn=kwargs.get("dsn") or INSTITUTION_B_DSN, institution="b", pool=kwargs.get("pool")))
```

A subtlety: the **registry name is not the same as `provider.id`**. `institution-a` and
`institution-b` are two distinct registry names, but both build a `PostgresProvider`
whose `provider.id == "postgres"` (`postgres.py:528`). That is why `/connectors` reports
the registry name as `id`, not `provider.id`, which would collide for the two
institutions (`status.py:12-13`).

`status.list_connector_status()` (`status.py:70-73`) auto-discovers every registered
connector: it iterates `list_connectors()` and probes each `health_check()`
concurrently, bounded by a 5-second timeout (`_HEALTH_TIMEOUT_S`, `status.py:25`) so an
unreachable source can never hang the endpoint. The served shape is
`{id, name, capabilities, health, latency_ms}` only.

---

## The FHIR R4B subset (6 resource types)

Connectors normalize into a fixed subset of six R4B resource types. The set is defined
identically in three places (`mock_fhir.py:31-40`, `fhir/validate.py:30-44`,
`fhir/subset.py:10-15`) and re-validated at the `/intake` boundary against the
`fhir.resources.R4B` models:

| Resource type | Coverage key |
|---|---|
| `Patient` | patient |
| `Condition` | conditions |
| `MedicationStatement` | medications |
| `Observation` | observations |
| `AllergyIntolerance` | allergies |
| `Procedure` | procedures |

At the `/intake` boundary, `validate_fhir_resource` (`fhir/validate.py:48-72`)
re-validates each fetched dict: out-of-subset types are silently filtered, and in-subset
but invalid resources are dropped as an honest data gap rather than returned as a 4xx.

---

## Two different schemas, one connector

`PostgresProvider` (`postgres.py:509`) is a single class that reads two deliberately
divergent institution schemas, selected by the `institution` constructor arg (`"a"` or
`"b"`, lowercased at `postgres.py:546`). `fetch_patient` branches at `postgres.py:570-579`:

```python
if self._institution == "a":
    patient_row, related = await _fetch_raw_a(conn, patient_id)
    resources, warnings = _translate_a(patient_row, related)
elif self._institution == "b":
    pt_row, events = await _fetch_raw_b(conn, patient_id)
    resources, warnings = _translate_b(pt_row, events)
else:
    raise ConnectorDataError(...)
```

The two schemas are genuinely different shapes.

### Institution A: normalized, one table per resource

`seeds/institution_a.sql` is EMR-style, with a separate table per resource type:

```sql
CREATE TABLE patients (
    patient_id    VARCHAR(64) PRIMARY KEY,
    date_of_birth DATE,
    sex           VARCHAR(10)         -- 'M', 'F', or other
);
CREATE TABLE diagnoses (
    diagnosis_id VARCHAR(64) PRIMARY KEY,
    patient_id   VARCHAR(64) NOT NULL REFERENCES patients(patient_id),
    icd10_code   VARCHAR(20) NOT NULL,
    description  TEXT,
    status       VARCHAR(20) DEFAULT 'active'
);
-- plus prescriptions, lab_results, drug_allergies, procedures_done
```

`_fetch_raw_a` (`postgres.py:444`) does one `fetchrow` on `patients` (raising
`ConnectorDataError` if the patient is not found) plus five separate `fetch` queries,
each `WHERE patient_id = $1`. `_translate_a` (`postgres.py:164`) maps each table to its
resource type: `diagnoses`→Condition (ICD-10), `prescriptions`→MedicationStatement
(RxNorm), `lab_results`→Observation (LOINC), `drug_allergies`→AllergyIntolerance,
`procedures_done`→Procedure. Note `drug_allergies` has no status column, so allergy
`clinicalStatus` is hard-coded `"active"` (`postgres.py:256`), and `procedures_done`
records only completed work, so procedure `status` is hard-coded `"completed"`
(`postgres.py:278`).

### Institution B: flat legacy single table

`seeds/institution_b.sql` is a legacy layout where *all* clinical events live in one
table, discriminated by `event_class`:

```sql
CREATE TABLE pt_registry (
    pt_ref      CHAR(12) PRIMARY KEY,   -- fixed-width, right-padded with spaces
    dob         VARCHAR(10),            -- ISO date string 'YYYY-MM-DD'
    gender_code CHAR(1)                 -- 'M', 'F', or 'U'
);
CREATE TABLE clinical_events (
    event_id    SERIAL      PRIMARY KEY,
    pt_ref      CHAR(12)    NOT NULL REFERENCES pt_registry(pt_ref),
    event_class VARCHAR(10) NOT NULL,   -- 'DX', 'RX', 'LAB', 'ALLERGY', 'PROC'
    code        VARCHAR(50) NOT NULL,
    code_system VARCHAR(20),
    num_value   NUMERIC,
    unit_val    VARCHAR(20),
    status_flag VARCHAR(20),
    event_date  DATE
);
```

`_fetch_raw_b` (`postgres.py:488`) does a `fetchrow` on `pt_registry WHERE
TRIM(pt_ref) = $1` (the `TRIM` handles the fixed-width `CHAR` padding) plus a single
`fetch` of all `clinical_events` for the patient. `_translate_b` (`postgres.py:300`)
iterates the events and dispatches on `event_class`: `DX`→Condition, `RX`→Medication
Statement, `LAB`→Observation, `ALLERGY`→AllergyIntolerance, `PROC`→Procedure. An unknown
class is not dropped silently, it appends a warning. Because B overloads one `status_flag`
column across every event class, the connector coerces it per type with small pure
helpers (`_observation_status`, `_allergy_clinical_status`, `_procedure_status`), each
defaulting unknown tokens to a safe value rather than dropping the record.

### Same output, proven

Both branches produce the identical searchset bundle and the same provenance and
coverage computation. `_iso_date` (`postgres.py:72`) coerces both A's `datetime.date`
and B's VARCHAR string to the same ISO `yyyy-mm-dd`, so `birthDate` compares equal across
the two schemas. The seeds make this concrete: the demo patient `DEMO-001` is seeded in
**both** institutions with the same clinical profile (E11/I10 diagnoses, Metformin
860975 and Lisinopril 29046, A1c 7.4% and Creatinine 0.9, an Amoxicillin allergy
372687004, an ophthalmic exam 36228007), stored as six tables in A and as eight
`clinical_events` rows in B. Same patient, same normalized output, two completely
different source layouts.

---

## The SELECT-only `umraa_reader` security model

Read-only access is enforced in two layers (`postgres.py:514-526`):

1. **Wire-level (the enforced invariant the tests pin).** Every query runs inside
   `async with conn.transaction(readonly=True)` (`postgres.py:569`), a Postgres
   `BEGIN READ ONLY` transaction that blocks INSERT/UPDATE/DELETE/DDL **regardless of the
   connecting role's grants**. No connector exposes a write method.
2. **Role-level (defense-in-depth, deployment guidance).** The seeds create a SELECT-only
   role (`institution_a.sql:56-70`, `institution_b.sql:31-45`):

   ```sql
   CREATE ROLE umraa_reader LOGIN PASSWORD 'umraa_reader';
   GRANT CONNECT ON DATABASE institution_a TO umraa_reader;
   GRANT USAGE  ON SCHEMA public TO umraa_reader;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO umraa_reader;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO umraa_reader;
   ```

   Role creation is idempotent (guarded by `IF NOT EXISTS (SELECT 1 FROM pg_roles ...)`).
   The default DSNs already connect *as* this role
   (`postgresql://umraa_reader:umraa_reader@localhost:5433/institution_a` and `:5434/
   institution_b`, `config.py:25-29`). The local-dev password is intentionally trivial;
   deployments override the credential via `INSTITUTION_A_DSN` / `INSTITUTION_B_DSN`.

The runtime credential is whatever the operator passes via `dsn`; wiring the connector to
`umraa_reader` is deployment guidance, while the transaction-level guarantee holds no
matter the role. The pool is created lazily under a double-checked lock
(`asyncpg.create_pool(dsn, min_size=1, max_size=3)`, `postgres.py:553-563`) and
`aclose()` uses `pool.terminate()` so it can never block on a checked-out connection.

Related discipline: validation warnings interpolate only `type(exc).__name__`, never the
raw pydantic `ValidationError` (which echoes name/address/telecom), and `/connectors`
never echoes `HealthStatus.detail`.

---

## Document provenance spans

For document sources, provenance carries enough to highlight a citation back in the
original text.

### PDF: char-offset spans

`TextSpan` (`pdf.py:63-71`) records a `page` (1-based), `start` (inclusive char offset
into the page text), `end` (exclusive), and a `snippet`. The core invariant is
`page_text[start:end] == snippet`; `_trimmed_span` (`pdf.py:166`) trims whitespace from
the *offsets* (not just the snippet) so that invariant holds even for whitespace-padded
lines. `_span_dict` (`pdf.py:162`) stores `{page, start, end, snippet}` into
`Provenance.span`.

`PDFProvider` (`pdf.py:76`) advertises `PATIENT | MEDICATIONS | CONDITIONS` and extracts
per page via `pdfplumber`. A page that yields no extractable text raises
`ConnectorDataError(... "scanned PDF not supported")` (`pdf.py:117-120`). There is no OCR
and no LLM-based extraction. Each extracted Condition and Medication gets a `Provenance`
with `source_record_id = str(page_num)` and a `span`. This span is what the verifier can
later re-check verbatim against the source text, and what the frontend renders as a
clickable highlight.

### HL7v2: record-level only

`HL7v2Provider` (`hl7v2.py:19`) is a scaffold that advertises `PATIENT` only. `_parse_adt`
parses just the PID segment (id from PID-3, name PID-5, DOB PID-7, gender PID-8) and
refuses to fabricate a `Patient/unknown` if PID-3 is empty. Its provenance carries
`source_record_id` but **no `span`**: char-offset spans are PDF-only, HL7v2 provenance is
record-level. The connector always reports `partial=True` and self-advertises the
scaffold limitation in a warning; full HL7v2-to-FHIR mapping is roadmap.

---

## The full source list

Five registered connectors built from four connector classes:

| Registry name | Class | `provider.id` | Capabilities | Default seeded source |
|---|---|---|---|---|
| `mock-fhir` | `MockFHIRProvider` | `mock-fhir` | all 6 | HAPI FHIR R4 server `https://hapi.fhir.org/baseR4`, snapshot-first from `seeds/mock_fhir_snapshot.json` |
| `pdf` | `PDFProvider` | `pdf` | PATIENT, MEDICATIONS, CONDITIONS | `seeds/sample_clinical.pdf` |
| `hl7v2` | `HL7v2Provider` | `hl7v2` | PATIENT only | `SAMPLE_ADT_A01`, an ADT^A01 message |
| `institution-a` | `PostgresProvider(institution="a")` | `postgres` | all 6 | `INSTITUTION_A_DSN` (port 5433, db `institution_a`) |
| `institution-b` | `PostgresProvider(institution="b")` | `postgres` | all 6 | `INSTITUTION_B_DSN` (port 5434, db `institution_b`) |

`mock-fhir` fetches all six resource types from the HAPI server (for
`MedicationStatement` it searches by `subject`) and standardizes the medication resource
on `MedicationStatement`.

---

## Adding a connector

1. Create `providers/<name>.py` with `class <Name>Provider(Provider)` (subclass
   `base.Provider`).
2. Set the class attrs `id: str` and `capabilities: Capability` (OR the relevant
   `Capability` flags, `base.py:9-15`).
3. Implement `async def fetch_patient(self, patient_id) -> FetchResult`: fetch the source
   data, normalize it into the six-type R4B subset dicts, build the
   `{"resourceType": "Bundle", "type": "searchset", "entry": [...]}` bundle, and populate
   `provenance` (a list of `Provenance`; add a `span` dict for char-offset document
   sources, à la `pdf._span_dict`) and `coverage` (per advertised capability). Raise
   `ConnectorUnavailable` for unreachable sources and `ConnectorDataError` for data that
   cannot be normalized.
4. Implement `async def health_check(self) -> HealthStatus` (`ok`, `latency_ms`, optional
   internal-only `detail`).
5. Override `async def aclose(self)` if you open a long-lived resource (a pool or client)
   so the `/connectors` prober can dispose of it (`base.py:72-79`).
6. Register the connector in `providers/__init__.py` via
   `register("<registry-name>", factory)`, where `factory` is a callable/lambda taking
   `**kwargs` and returning the provider. Supply a seeded default source so it runs
   standalone, with `kwargs` overriding (the pattern at `__init__.py:29-46`). Add any new
   public symbols to `__all__` (`__init__.py:48-66`).

The connector is then auto-discovered by `status.list_connector_status()` and selectable
via `build("<registry-name>", **kwargs)`. Fetched resources pass through
`validate_fhir_resource` at the `/intake` boundary: out-of-subset types are silently
filtered, and in-subset but invalid ones are dropped as honest gaps.

---

### Relevant files

- `backend/app/providers/{base,registry,__init__,mock_fhir,postgres,pdf,hl7v2,status}.py`
- `backend/app/fhir/{validate,subset}.py`
- `backend/app/seeds/{institution_a.sql,institution_b.sql,sample_hl7.py}`
- `backend/app/config.py`
