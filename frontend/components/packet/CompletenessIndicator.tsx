"use client"

import { CheckCircle2, HelpCircle } from "lucide-react"

import type { CategoryCompleteness } from "@/lib/api/types"

interface CompletenessIndicatorProps {
  completeness: CategoryCompleteness[]
}

/**
 * Per-category documentation completeness. A category that is NOT documented is
 * rendered as "not documented / unknown" — never "none" — preserving the
 * clinical invariant that absence of data is unknown, not negative.
 */
export function CompletenessIndicator({
  completeness,
}: CompletenessIndicatorProps) {
  if (completeness.length === 0) return null

  return (
    <aside
      aria-label="Data completeness"
      className="rounded-lg border border-border bg-bg-surface p-5"
    >
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Data Completeness
      </h3>
      <ul className="mt-3 space-y-2.5">
        {completeness.map((item) => (
          <li key={item.category} className="flex items-start gap-2.5">
            {item.documented ? (
              <CheckCircle2
                size={16}
                className="mt-0.5 shrink-0 text-[var(--success)]"
                aria-hidden="true"
              />
            ) : (
              <HelpCircle
                size={16}
                className="mt-0.5 shrink-0 text-[var(--text-muted)]"
                aria-hidden="true"
              />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground">
                {item.category}
              </p>
              {!item.documented && (
                <p className="text-xs text-[var(--text-secondary)]">
                  {item.gap_note ?? "Not documented / unknown"}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </aside>
  )
}
