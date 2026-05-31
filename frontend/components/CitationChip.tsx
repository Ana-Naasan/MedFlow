"use client";

import { useState } from "react";

import type { Citation } from "../lib/types";
import { EvidencePanel } from "./EvidencePanel";

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

  const chipClass = `chip-interactive ${isKnowledge ? "chip-knowledge" : "chip-patient-fact"}`;

  return (
    <>
      <button
        type="button"
        className={chipClass}
        onClick={isKnowledge ? () => setOpen(true) : undefined}
        {...(isKnowledge ? { "aria-haspopup": "dialog" as const } : {})}
        data-citation-type={isKnowledge ? "knowledge" : "patient-fact"}
      >
        {isKnowledge ? <ExternalLinkIcon /> : <PersonIcon />}
        {citation.label ?? citation.ref}
      </button>
      {open && isKnowledge && (
        <EvidencePanel
          evidenceId={citation.ref}
          label={citation.label}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
