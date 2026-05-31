"use client"

import { AlertTriangle, Loader2, ScrollText } from "lucide-react"

import { useAudit } from "@/lib/api/hooks"
import type { AuditEvent } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"

/**
 * Recent entries from the immutable audit log backed by `GET /audit?limit=50`
 * (useAudit(50)). Rendered newest first.
 *
 * Every read of patient data emits an AuditEvent, so this is the operator-facing
 * PHI-access trail. We format `occurred_at` for display but fall back to the raw
 * string if it is not a parseable date — never dropping the value.
 */
function formatTimestamp(occurredAt: string): string {
  const parsed = new Date(occurredAt)
  if (Number.isNaN(parsed.getTime())) return occurredAt
  return parsed.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

/** Sort newest first by `occurred_at`; ties and unparseable dates keep order. */
function sortedNewestFirst(events: AuditEvent[]): AuditEvent[] {
  return [...events].sort((a, b) => {
    const ta = new Date(a.occurred_at).getTime()
    const tb = new Date(b.occurred_at).getTime()
    if (Number.isNaN(ta) || Number.isNaN(tb)) return 0
    return tb - ta
  })
}

export function AuditLogTable() {
  const { data, isPending, isError, error } = useAudit(50)

  const events = data ? sortedNewestFirst(data) : []

  return (
    <section aria-labelledby="util-audit">
      <h2
        id="util-audit"
        className="mb-3 flex items-center gap-2 text-lg font-semibold"
      >
        <ScrollText className="size-5 text-[var(--mf-accent)]" aria-hidden />
        Audit log
        <span className="text-sm font-normal" style={{ color: "var(--mf-ink-soft)" }}>
          (recent reads, newest first)
        </span>
      </h2>

      {isPending ? (
        <div
          className="mf-surface-card flex items-center gap-2 p-4 text-sm"
          style={{ color: "var(--mf-ink-soft)" }}
        >
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading audit events…
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
              : "Could not load the audit log."}
          </span>
        </div>
      ) : events.length === 0 ? (
        <div className="mf-surface-card p-4 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          No audit events recorded yet.
        </div>
      ) : (
        <div className="mf-surface-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr
                className="border-b-2"
                style={{ borderColor: "var(--mf-ink)", background: "var(--mf-paper-2)" }}
              >
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Event</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Patient</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Resource</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Actor</th>
                <th className="mf-eyebrow px-4 py-3 text-right !text-[10px]">When</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr
                  key={event.id}
                  className="border-b last:border-0"
                  style={{ borderColor: "var(--mf-paper-2)" }}
                >
                  <td className="px-4 py-3 font-medium">{event.event_type}</td>
                  <td className="px-4 py-3 font-mono text-xs" style={{ color: "var(--mf-ink-soft)" }}>
                    {event.patient_id || "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs break-all" style={{ color: "var(--mf-ink-soft)" }}>
                    {event.resource_ref || "—"}
                  </td>
                  <td className="px-4 py-3">{event.actor || "—"}</td>
                  <td
                    className="px-4 py-3 text-right tabular-nums whitespace-nowrap text-xs"
                    style={{ color: "var(--mf-ink-soft)" }}
                  >
                    {formatTimestamp(event.occurred_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
