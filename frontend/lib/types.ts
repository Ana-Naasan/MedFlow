export interface Citation {
  kind: string;
  ref: string;
  label: string | null;
  source_span?: Span | null;
}

export interface Hypothesis {
  id: string;
  title: string;
  why: string;
  severity: string;
  confidence: string;
  citations: Citation[];
}

export interface Span {
  page: number;
  start: number;
  end: number;
  snippet: string;
}

export interface CategoryCompleteness {
  category: string;
  documented: boolean;
  gap_note: string | null;
}

export interface DecisionPacket {
  patient_id: string;
  summary_markdown: string;
  hypotheses: Hypothesis[];
  data_gaps: string[];
  completeness?: CategoryCompleteness[];
  cache_status: string | null;
}
