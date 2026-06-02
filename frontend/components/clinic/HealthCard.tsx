"use client"

import { Activity, CircleCheck, CircleX, Loader2 } from "lucide-react"

import { useHealth } from "@/lib/api/hooks"
import { Badge } from "@/components/ui/badge"

/**
 * Backend liveness panel backed by `GET /health` (useHealth()).
 *
 * The health body is an untyped `Record<string, string>`. We treat the backend
 * as healthy only when an explicit affirmative status value is present; anything
 * else (including a missing status) is rendered as a non-healthy / unknown
 * state — never silently "ok" — and the raw key/value pairs are listed so the
 * operator can see exactly what the backend reported.
 */
function isHealthyValue(value: string): boolean {
  const v = value.trim().toLowerCase()
  return v === "ok" || v === "healthy" || v === "up" || v === "true" || v === "pass"
}

export function HealthCard() {
  const { data, isPending, isError, error } = useHealth()

  const entries = data ? Object.entries(data) : []
  // Healthy only when the backend reported at least one field and every
  // reported field is affirmative. An empty/partial body stays "unknown".
  const healthy =
    entries.length > 0 && entries.every(([, value]) => isHealthyValue(value))

  return (
    <section aria-labelledby="util-health">
      <h2
        id="util-health"
        className="mb-3 flex items-center gap-2 text-lg font-semibold"
      >
        <Activity className="size-5 text-[var(--mf-accent)]" aria-hidden />
        System health
      </h2>

      <div className="mf-surface-card p-4">
        {isPending ? (
          <div
            className="flex items-center gap-2 text-sm"
            style={{ color: "var(--mf-ink-soft)" }}
          >
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Checking backend status…
          </div>
        ) : isError ? (
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="destructive" className="gap-1">
              <CircleX className="size-3" aria-hidden />
              Unreachable
            </Badge>
            <span className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
              {error instanceof Error
                ? error.message
                : "The backend health endpoint could not be reached."}
            </span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {healthy ? (
                <Badge
                  className="gap-1 border-transparent text-white"
                  style={{ background: "var(--success)" }}
                >
                  <CircleCheck className="size-3" aria-hidden />
                  Healthy
                </Badge>
              ) : (
                <Badge variant="destructive" className="gap-1">
                  <CircleX className="size-3" aria-hidden />
                  {entries.length === 0 ? "Unknown" : "Degraded"}
                </Badge>
              )}
            </div>

            {entries.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                The backend responded but reported no status fields.
              </p>
            ) : (
              <dl className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
                {entries.map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-3 border-b py-1 last:border-0"
                    style={{ borderColor: "var(--mf-paper-2)" }}
                  >
                    <dt
                      className="font-mono text-xs"
                      style={{ color: "var(--mf-ink-soft)" }}
                    >
                      {key}
                    </dt>
                    <dd className="font-medium tabular-nums">{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
