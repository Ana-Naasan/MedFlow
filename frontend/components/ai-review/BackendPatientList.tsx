"use client"

import Link from "next/link"
import { Database, ChevronRight, AlertTriangle, RefreshCw } from "lucide-react"

import { usePatients } from "@/lib/api/hooks"
import { Button } from "@/components/ui/button"

/**
 * Lists real backend patient ids from `GET /patients`. Each row deep-links to
 * that patient's AI Review tab (`/patients/{id}/packet`), which is the surface
 * that renders the cited decision packet.
 *
 * Renders explicit loading / error / empty states. An empty backend is not a
 * failure — it prompts the operator to run intake (handled by the sibling
 * IntakePanel), never implying "no patients exist" as a clinical fact.
 */
export function BackendPatientList() {
  const { data: patientIds, isPending, isError, error, refetch } = usePatients()

  return (
    <section aria-label="Backend patients" className="mf-surface-card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div
            className="flex size-9 items-center justify-center rounded-lg bg-[var(--mf-accent-soft)]"
            aria-hidden="true"
          >
            <Database className="size-4 text-[var(--mf-accent)]" />
          </div>
          <div>
            <h2 className="mf-display text-lg font-semibold leading-tight">
              Backend patients
            </h2>
            <p className="text-xs" style={{ color: "var(--mf-ink-soft)" }}>
              Records ingested into the decision-support backend
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void refetch()}
          disabled={isPending}
          aria-label="Refresh patient list"
        >
          <RefreshCw className="size-3.5" aria-hidden="true" />
          Refresh
        </Button>
      </div>

      {isPending ? (
        <ul className="space-y-2" aria-busy="true" aria-label="Loading patients">
          {[0, 1, 2].map((i) => (
            <li
              key={i}
              className="h-12 animate-pulse rounded-lg border border-border bg-bg-subtle"
            />
          ))}
        </ul>
      ) : isError ? (
        <div
          className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4"
          role="alert"
        >
          <AlertTriangle
            className="mt-0.5 size-4 shrink-0 text-destructive"
            aria-hidden="true"
          />
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              Could not load patients
            </p>
            <p className="text-xs" style={{ color: "var(--mf-ink-soft)" }}>
              {error instanceof Error ? error.message : "The backend is unreachable."}
            </p>
            <Button variant="outline" size="sm" onClick={() => void refetch()}>
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Try again
            </Button>
          </div>
        </div>
      ) : patientIds.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-bg-subtle p-6 text-center">
          <p className="text-sm font-medium text-foreground">
            No patients ingested yet
          </p>
          <p
            className="mx-auto mt-1 max-w-sm text-xs"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            Import a patient from a connector to generate a cited decision packet
            for review.
          </p>
        </div>
      ) : (
        <ul className="space-y-2" role="list">
          {patientIds.map((id) => (
            <li key={id}>
              <Link
                href={`/patients/${encodeURIComponent(id)}/packet`}
                className="group flex items-center justify-between gap-3 rounded-lg border border-border bg-bg-surface px-4 py-3 transition-colors hover:border-[var(--mf-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
              >
                <span className="flex items-center gap-2.5 min-w-0">
                  <Database
                    className="size-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <span className="truncate font-mono text-sm font-medium text-foreground">
                    {id}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1 text-xs font-semibold text-[var(--mf-accent)]">
                  Open AI Review
                  <ChevronRight
                    className="size-3.5 transition-transform group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
