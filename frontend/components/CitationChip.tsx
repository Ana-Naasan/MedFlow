"use client";

import { useState } from "react";

import type { Citation } from "../lib/types";
import { EvidencePanel } from "./EvidencePanel";
import { PdfHighlightPanel } from "./PdfHighlightPanel";

interface CitationChipProps {
  citation: Citation;
  patientId: string;
}

function ExternalLinkIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false">
      <path d="M7 1h4v4M11 1L5 7M3 3H1v8h8V9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true" focusable="false">
      <circle cx="6" cy="3.5" r="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1 11c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function CitationChip({ citation }: CitationChipProps) {
  const [open, setOpen] = useState(false);
  const isKnowledge = citation.kind === "evidence";
  const isResource = citation.kind === "resource";
  const span = citation.source_span ?? null;
  // INVARIANT (#97): a chip must never look interactive but do nothing.
  // - evidence → opens the EvidencePanel
  // - resource WITH a source_span → opens the PdfHighlightPanel
  // - resource WITHOUT a source_span → static, non-interactive label
  const hasHighlight = isResource && span != null;
  const isInteractive = isKnowledge || hasHighlight;

  const label = citation.label ?? citation.ref;
  const icon = isKnowledge ? <ExternalLinkIcon /> : <PersonIcon />;
  const dataType = isKnowledge ? "knowledge" : "patient-fact";
  const variant = isKnowledge ? "chip-knowledge" : "chip-patient-fact";

  if (!isInteractive) {
    return (
      <span
        className={`chip-static ${variant}`}
        data-citation-type={dataType}
        data-interactive="false"
      >
        {icon}
        {label}
      </span>
    );
  }

  return (
    <>
      <button
        type="button"
        className={`chip-interactive ${variant}`}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        data-citation-type={dataType}
      >
        {icon}
        {label}
      </button>
      {open && isKnowledge && (
        <EvidencePanel
          evidenceId={citation.ref}
          label={citation.label}
          onClose={() => setOpen(false)}
        />
      )}
      {open && hasHighlight && span && (
        <PdfHighlightPanel
          span={span}
          label={citation.label}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
