"use client"

import type { ReactNode } from "react"

import { TierBadge } from "@/components/packet/tier-badge"
import type { Hypothesis } from "@/lib/api/types"

export interface HypothesisCardProps {
  /** The cited, tiered hypothesis to render. */
  hypothesis: Hypothesis
  /**
   * Citation chips rendered in the card's evidence row. A later agent mounts
   * the interactive chips here; until then the row is simply empty.
   *
   * INVARIANT: the parent must filter out hypotheses with zero citations
   * before rendering this card — a claim with no resolvable citation is never
   * shown. This slot is for the rendered chip elements, not the raw data.
   */
  citations?: ReactNode
  /**
   * Confirm / dismiss controls. A later agent mounts the action buttons +
   * keyboard handling here; rendered in a dedicated action row when present.
   */
  actions?: ReactNode
}

/**
 * One hypothesis in the differential. Renders the associative title + "why"
 * narrative and the source-derived severity / confidence tier badges.
 *
 * The card is keyboard-focusable (`tabIndex={0}`) and carries a stable
 * `data-hypothesis-id` so the later keyboard-navigation agent can target it.
 * Citation chips and confirm/dismiss controls are injected via the `citations`
 * and `actions` slots so this component stays a stable, presentational shell.
 */
export function HypothesisCard({
  hypothesis,
  citations,
  actions,
}: HypothesisCardProps) {
  return (
    <article
      data-hypothesis-id={hypothesis.id}
      tabIndex={0}
      aria-label={hypothesis.title}
      // Surface the review shortcuts to assistive tech (the visible KeyboardHint
      // is sighted-only): j/k move · c ack · d dismiss · Enter open citation.
      aria-keyshortcuts="j k c d Enter"
      className="rounded-lg border border-border bg-bg-surface p-5 outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Hypothesis · {hypothesis.id}
      </p>

      <h3 className="mt-1 text-base font-semibold leading-snug text-foreground">
        {hypothesis.title}
      </h3>

      {/* Associative narrative — language is "may be associated", never causal. */}
      <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
        {hypothesis.why}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <TierBadge prefix="Severity" value={hypothesis.severity} />
        <TierBadge prefix="Confidence" value={hypothesis.confidence} />
      </div>

      {/* Citation slot — interactive chips mounted by a later agent. */}
      {citations != null && (
        <div
          className="mt-4 flex flex-wrap gap-2"
          role="group"
          aria-label="Citations"
          data-slot="hypothesis-citations"
        >
          {citations}
        </div>
      )}

      {/* Action slot — confirm / dismiss controls mounted by a later agent. */}
      {actions != null && (
        <div
          className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3"
          role="group"
          aria-label="Review actions"
          data-slot="hypothesis-actions"
        >
          {actions}
        </div>
      )}
    </article>
  )
}
