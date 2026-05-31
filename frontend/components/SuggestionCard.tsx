"use client";

import type { Hypothesis } from "../lib/types";
import { CitationChip } from "./CitationChip";

interface SuggestionCardProps {
  hypothesis: Hypothesis;
  patientId: string;
}

export function SuggestionCard({ hypothesis, patientId }: SuggestionCardProps) {
  return (
    <article className="panel card stack">
      <div>
        <p className="eyebrow">Hypothesis · {hypothesis.id}</p>
        <h2>{hypothesis.title}</h2>
        <p>{hypothesis.why}</p>
        <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
          <span className="badge badge-severity">{hypothesis.severity}</span>
          <span className="badge badge-confidence">{hypothesis.confidence} confidence</span>
        </div>
      </div>
      <div className="chip-row">
        {hypothesis.citations.map((citation) => (
          <CitationChip key={citation.ref} citation={citation} patientId={patientId} />
        ))}
      </div>
    </article>
  );
}
