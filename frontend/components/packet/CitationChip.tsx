"use client"

import { ExternalLink, User } from "lucide-react"

import { cn } from "@/lib/utils"
import type { Citation } from "@/lib/api/types"

interface CitationChipProps {
  /** The resolvable citation this chip points at. */
  citation: Citation
  /** Opens the evidence drawer for this citation. */
  onOpen: (citation: Citation) => void
}

/**
 * A single clickable citation chip in a hypothesis's evidence row.
 *
 * Two source kinds are styled distinctly so the clinician can tell at a glance
 * whether a claim is backed by the patient's own record or by external clinical
 * knowledge:
 *   - `evidence` (knowledge card) → primary/accent tint + external-link icon
 *   - `resource` (a FHIR resource from the patient's chart) → neutral tint +
 *     person icon
 *
 * Every chip is interactive: clicking resolves the citation in the
 * EvidenceDrawer. The "no resolvable citation → not shown" invariant is upheld
 * upstream (the page filters hypotheses with zero citations before rendering),
 * so a rendered chip always has a resolvable target.
 */
export function CitationChip({ citation, onOpen }: CitationChipProps) {
  const isKnowledge = citation.kind === "evidence"
  const label = citation.label ?? citation.ref

  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      aria-haspopup="dialog"
      data-citation-kind={isKnowledge ? "knowledge" : "patient-fact"}
      title={citation.ref}
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-4xl border px-2.5 py-1 text-xs font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1",
        isKnowledge
          ? "border-[color-mix(in_oklch,var(--accent)_28%,transparent)] bg-[color-mix(in_oklch,var(--accent)_10%,transparent)] text-[var(--accent)] hover:bg-[color-mix(in_oklch,var(--accent)_16%,transparent)]"
          : "border-border bg-bg-subtle text-[var(--text-secondary)] hover:bg-muted hover:text-foreground"
      )}
    >
      {isKnowledge ? (
        <ExternalLink size={12} aria-hidden="true" className="shrink-0" />
      ) : (
        <User size={12} aria-hidden="true" className="shrink-0" />
      )}
      <span className="truncate">{label}</span>
    </button>
  )
}
