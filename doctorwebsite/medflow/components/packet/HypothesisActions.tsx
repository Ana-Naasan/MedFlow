"use client"

import { Check, Loader2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useConfirmHypothesis, useDismissHypothesis } from "@/lib/api/hooks"
import type { Hypothesis } from "@/lib/api/types"

interface HypothesisActionsProps {
  hypothesis: Hypothesis
  /** Backend patient id the confirm/dismiss POSTs are scoped to. */
  patientId: string
}

/**
 * Confirm / Dismiss controls for one hypothesis.
 *
 * The labels stay associative and non-prescriptive — "Acknowledge" (the
 * clinician has reviewed and accepts the association for follow-up) and
 * "Dismiss" (set it aside) — never "Stop drug X" or any directive. The packet
 * query is auto-invalidated by the mutation hooks on success, so a dismiss that
 * cascades to sibling hypotheses (group dismiss returns `dismissed_ids`) is
 * reflected by the refetch removing them; no local optimistic removal needed.
 */
export function HypothesisActions({
  hypothesis,
  patientId,
}: HypothesisActionsProps) {
  const confirm = useConfirmHypothesis()
  const dismiss = useDismissHypothesis()

  const acting = confirm.isPending || dismiss.isPending
  const errored = confirm.isError || dismiss.isError

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={acting}
          aria-label={`Acknowledge for review: ${hypothesis.title}`}
          onClick={() =>
            confirm.mutate({ id: hypothesis.id, patientId })
          }
          className="text-[var(--success)] hover:text-[var(--success)]"
        >
          {confirm.isPending ? (
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          ) : (
            <Check size={14} aria-hidden="true" />
          )}
          Acknowledge
        </Button>

        <Button
          type="button"
          size="sm"
          variant="ghost"
          disabled={acting}
          aria-label={`Dismiss: ${hypothesis.title}`}
          onClick={() =>
            dismiss.mutate({ id: hypothesis.id, patientId })
          }
          className="text-[var(--text-secondary)]"
        >
          {dismiss.isPending ? (
            <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          ) : (
            <X size={14} aria-hidden="true" />
          )}
          Dismiss
        </Button>
      </div>

      {errored && (
        <p role="alert" className="text-xs text-[var(--danger)]">
          Could not record that action. Please try again.
        </p>
      )}
    </div>
  )
}
