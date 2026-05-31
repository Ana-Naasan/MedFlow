"use client"

import { AlertTriangle, Loader2, Plug } from "lucide-react"

import { useConnectors } from "@/lib/api/hooks"
import { Badge } from "@/components/ui/badge"

/**
 * Registered data-source connectors backed by `GET /connectors` (useConnectors()).
 *
 * The endpoint returns an untyped `Record<string, unknown>[]`. Each connector's
 * shape is unknown, so we extract a best-effort id from the common id-bearing
 * keys and render every remaining field as a label/value chip rather than
 * assuming a fixed schema.
 */
const ID_KEYS = ["id", "name", "connector", "connector_id", "type", "key"] as const

function connectorId(connector: Record<string, unknown>, index: number): string {
  for (const key of ID_KEYS) {
    const value = connector[key]
    if (typeof value === "string" && value.length > 0) return value
  }
  return `connector-${index + 1}`
}

function formatFieldValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "string") return value
  if (typeof value === "number" || typeof value === "boolean") return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

export function ConnectorsList() {
  const { data, isPending, isError, error } = useConnectors()

  return (
    <section aria-labelledby="util-connectors">
      <h2
        id="util-connectors"
        className="mb-3 flex items-center gap-2 text-lg font-semibold"
      >
        <Plug className="size-5 text-[var(--mf-accent)]" aria-hidden />
        Connectors
      </h2>

      {isPending ? (
        <div className="mf-surface-card flex items-center gap-2 p-4 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading connectors…
        </div>
      ) : isError ? (
        <div className="mf-surface-card flex flex-wrap items-center gap-3 p-4">
          <Badge variant="destructive" className="gap-1">
            <AlertTriangle className="size-3" aria-hidden />
            Failed to load
          </Badge>
          <span className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            {error instanceof Error
              ? error.message
              : "Could not load the connector registry."}
          </span>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="mf-surface-card p-4 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          No connectors are registered.
        </div>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-2">
          {data.map((connector, index) => {
            const id = connectorId(connector, index)
            const fields = Object.entries(connector).filter(
              ([key]) => key !== "id" && key !== "name" && key !== "connector",
            )
            return (
              <li key={id} className="mf-surface-card p-4">
                <p className="flex items-center gap-1.5 text-sm font-semibold">
                  <Plug className="size-3.5 opacity-60" aria-hidden />
                  <span className="font-mono">{id}</span>
                </p>
                {fields.length > 0 && (
                  <dl className="mt-2 space-y-1 text-xs">
                    {fields.map(([key, value]) => (
                      <div key={key} className="flex items-start justify-between gap-3">
                        <dt style={{ color: "var(--mf-ink-soft)" }}>{key}</dt>
                        <dd className="text-right font-medium break-all">
                          {formatFieldValue(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
