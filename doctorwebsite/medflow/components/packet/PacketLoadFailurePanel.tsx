"use client"

import { AlertCircle } from "lucide-react"

import type { PacketLoadDiagnostic } from "@/lib/api/hooks"

interface PacketLoadFailurePanelProps {
  diag: PacketLoadDiagnostic
}

/**
 * Explicit, actionable diagnostic for a packet-fetch failure (status / URL /
 * elapsed / body). Ported from the reference frontend so the operator can see
 * WHY the request failed without leaving the page.
 *
 * The hint heuristic maps the observed HTTP status to the most likely cause:
 *   401/403 → bearer-token mismatch
 *   404     → wrong patient id OR wrong base URL
 *   5xx     → backend error
 *   none    → no response: backend unreachable / wrong base URL / CORS
 */
export function PacketLoadFailurePanel({ diag }: PacketLoadFailurePanelProps) {
  const hint = describeFailure(diag.status)
  const bodyText = formatBody(diag.body)

  return (
    <section
      role="alert"
      aria-label="Packet load failure"
      data-testid="packet-load-failure"
      className="rounded-lg border border-[color-mix(in_oklch,var(--danger)_28%,transparent)] bg-[color-mix(in_oklch,var(--danger)_8%,transparent)] p-5"
    >
      <div className="flex items-start gap-2.5">
        <AlertCircle
          size={18}
          className="mt-0.5 shrink-0 text-[var(--danger)]"
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-foreground">
            Failed to load packet.
          </h2>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{hint}</p>

          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
            <dt className="font-medium text-muted-foreground">Status</dt>
            <dd
              data-testid="packet-failure-status"
              className="font-mono text-foreground"
            >
              {diag.status !== undefined
                ? String(diag.status)
                : "— (no response)"}
            </dd>

            <dt className="font-medium text-muted-foreground">URL</dt>
            <dd
              data-testid="packet-failure-url"
              className="truncate font-mono text-foreground"
            >
              {diag.url || "—"}
            </dd>

            <dt className="font-medium text-muted-foreground">Elapsed</dt>
            <dd
              data-testid="packet-failure-elapsed"
              className="font-mono text-foreground"
            >
              {diag.elapsedMs} ms
            </dd>
          </dl>

          {bodyText !== null && (
            <div className="mt-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Response body
              </p>
              <pre
                data-testid="packet-failure-body"
                className="mt-1 max-h-48 overflow-auto rounded-md border border-border bg-bg-subtle p-3 font-mono text-xs text-foreground"
              >
                {bodyText}
              </pre>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function describeFailure(status: number | undefined): string {
  if (status === undefined) {
    return (
      "No response from the backend. Likely the API is unreachable, " +
      "NEXT_PUBLIC_API_BASE_URL is wrong, or a CORS preflight was blocked."
    )
  }
  if (status === 401 || status === 403) {
    return (
      "The backend rejected the request as unauthorized. Check that " +
      "NEXT_PUBLIC_API_TOKEN (frontend) matches the backend token in this " +
      "deployment."
    )
  }
  if (status === 404) {
    return (
      "The backend returned 404 for this route. Either the patient id is " +
      "not recognised, or NEXT_PUBLIC_API_BASE_URL points to a different API."
    )
  }
  if (status >= 500) {
    return "The backend reported a server error. Check the backend logs."
  }
  if (status >= 400) {
    return "The backend rejected the request."
  }
  return "Unexpected non-error response routed through the failure UI."
}

/** Stringify an error body for display; long bodies are truncated. */
function formatBody(body: unknown): string | null {
  if (body === null || body === undefined) return null
  let text: string
  if (typeof body === "string") {
    text = body
  } else {
    try {
      text = JSON.stringify(body, null, 2)
    } catch {
      text = String(body)
    }
  }
  const trimmed = text.trim()
  if (!trimmed) return null
  const max = 800
  return trimmed.length > max ? trimmed.slice(0, max) + "\n… (truncated)" : trimmed
}
