export interface Citation {
  kind: string;
  ref: string;
  label: string | null;
}

export interface Hypothesis {
  id: string;
  title: string;
  why: string;
  severity: string;
  confidence: string;
  citations: Citation[];
}

export interface DecisionPacket {
  patient_id: string;
  summary_markdown: string;
  hypotheses: Hypothesis[];
  data_gaps: string[];
  cache_status: string | null;
}
