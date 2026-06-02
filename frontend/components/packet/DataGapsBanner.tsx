"use client"

import { AlertTriangle } from "lucide-react"

interface DataGapsBannerProps {
  /** Free-text descriptions of data that could not be retrieved. */
  gaps: string[]
}

/**
 * Surfaces the packet's `data_gaps[]`. Absence of data is framed as "could not
 * be retrieved" / unknown — never "none" / "no risk".
 */
export function DataGapsBanner({ gaps }: DataGapsBannerProps) {
  if (gaps.length === 0) return null

  return (
    <aside
      role="status"
      aria-live="polite"
      aria-label="Data gaps"
      data-testid="data-gaps-banner"
      className="rounded-lg border border-[color-mix(in_oklch,var(--warning)_28%,transparent)] bg-[color-mix(in_oklch,var(--warning)_10%,transparent)] p-4"
    >
      <div className="flex items-start gap-2.5">
        <AlertTriangle
          size={16}
          className="mt-0.5 shrink-0 text-[var(--warning)]"
          aria-hidden="true"
        />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            Some data could not be retrieved from this source.
          </p>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-sm text-[var(--text-secondary)]">
            {gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  )
}
