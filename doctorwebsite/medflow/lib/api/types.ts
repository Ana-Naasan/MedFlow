/**
 * Hand-written types for the Umraa backend `/packet` body and a few other
 * endpoints whose response shapes are not described in the OpenAPI schema.
 *
 * The `DecisionPacket` is the product's core payload: a citation-tagged set of
 * tiered, associative hypotheses. Every clinical claim carries a resolvable
 * citation — these types preserve that structure so the UI can enforce the
 * "no resolvable citation → not shown" invariant.
 */

/**
 * Source location for a citation snippet (e.g. a PDF page span). All fields
 * are present together when the source is a document; otherwise the citation's
 * `source_span` is null/omitted.
 */
export interface Span {
  page: number;
  start: number;
  end: number;
  snippet: string;
}

/**
 * A resolvable pointer to a real source backing a clinical claim. `kind`/`ref`
 * identify the source (e.g. a FHIR resource type + id) so the UI can deep-link
 * to it. `label` may be null when the source provides no display name.
 */
export interface Citation {
  kind: string;
  ref: string;
  label: string | null;
  source_span?: Span | null;
}

/**
 * A cited, tiered hypothesis associating a symptom with drugs, interactions,
 * conditions, or procedures. Language is always associative ("may be
 * associated — consider reviewing"). `severity`/`confidence` are
 * source-derived tiers rendered as badges; do not editorialize them.
 */
export interface Hypothesis {
  id: string;
  title: string;
  why: string;
  severity: string;
  confidence: string;
  group?: string | null;
  citations: Citation[];
}

/**
 * Per-category documentation completeness. `documented: false` with a
 * `gap_note` means data is unknown / not documented — never "none"/"no risk".
 */
export interface CategoryCompleteness {
  category: string;
  documented: boolean;
  gap_note: string | null;
}

/**
 * The full decision packet returned by `GET /patients/{patient_id}/packet`.
 * This shape is NOT in the OpenAPI schema (the endpoint returns an untyped
 * JSON object), so it is defined here and cast at the hook boundary.
 */
export interface DecisionPacket {
  patient_id: string;
  summary_markdown: string;
  hypotheses: Hypothesis[];
  data_gaps: string[];
  completeness: CategoryCompleteness[];
  cache_status: string | null;
}

/**
 * Response of `GET /evidence/{evidence_id}` — a resolvable evidence snippet.
 *
 * The endpoint returns the raw knowledge card, which in practice is looser than
 * the core `{id,kind,ref,label}` quartet: it commonly also carries a `source`
 * (publisher/origin), a `snippet` (the displayable excerpt), and a `ref_url`
 * (external link). These are declared optional so the typed contract matches
 * what `EvidenceBody` reads defensively at runtime instead of diverging from it.
 */
export interface EvidenceSnippet {
  id: string;
  kind: string;
  ref: string;
  label: string;
  source?: string | null;
  snippet?: string | null;
  ref_url?: string | null;
}

/**
 * One entry from the immutable audit log (`GET /audit`), newest first.
 */
export interface AuditEvent {
  id: string;
  event_type: string;
  patient_id: string;
  resource_ref: string;
  actor: string;
  occurred_at: string;
}

/**
 * Body for `POST /intake`. `patient_id` overrides the stored ID; a UUID is
 * auto-generated when omitted.
 */
export interface IntakeRequest {
  connector: string;
  source_patient_id: string;
  patient_id?: string;
}

/**
 * Response of `POST /intake`.
 */
export interface IntakeResponse {
  patient_id: string;
  status: string;
  resource_count: number;
  hypothesis_ids?: string[];
}
