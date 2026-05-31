"use client";

import type { Hypothesis } from "../lib/types";
import { CitationChip } from "./CitationChip";

type ResolvedStatus = "confirmed" | "dismissed";

interface SuggestionCardProps {
  hypothesis: Hypothesis;
  patientId: string;
  onConfirm?: () => void;
  onDismiss?: () => void;
  /** Callback ref so the parent can store and focus the Approve button. */
  approveRef?: (el: HTMLButtonElement | null) => void;
  status?: ResolvedStatus | null;
  isActing?: boolean;
}

export function SuggestionCard({
  hypothesis,
  patientId,
  onConfirm,
  onDismiss,
  approveRef,
  status,
  isActing,
}: SuggestionCardProps) {
  const hasActions = onConfirm != null || onDismiss != null;
  const isResolved = status != null;

  return (
    <article
      className="panel card stack"
      aria-label={hypothesis.title}
    >
      <div>
        <p className="eyebrow">Hypothesis · {hypothesis.id}</p>
        <h2>{hypothesis.title}</h2>
        <p>{hypothesis.why}</p>
        <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
          <span className="badge badge-severity">{hypothesis.severity}</span>
          <span className="badge badge-confidence">
            {hypothesis.confidence} confidence
          </span>
        </div>
      </div>

      <div className="chip-row">
        {hypothesis.citations.map((citation) => (
          <CitationChip key={citation.ref} citation={citation} patientId={patientId} />
        ))}
      </div>

      {hasActions && !isResolved && (
        <div style={{ display: "flex", gap: "8px", marginTop: "8px" }} role="group" aria-label="Review actions">
          {onConfirm && (
            <button
              ref={approveRef}
              onClick={onConfirm}
              disabled={isActing}
              aria-label={`Approve: ${hypothesis.title}`}
            >
              Approve
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              disabled={isActing}
              aria-label={`Dismiss: ${hypothesis.title}`}
            >
              Dismiss
            </button>
          )}
        </div>
      )}

      {isResolved && (
        <p aria-live="polite" style={{ marginTop: "8px" }}>
          {status === "confirmed" ? "✓ Approved" : "✗ Dismissed"}
        </p>
      )}
    </article>
  );
}
