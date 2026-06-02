"use client"

import { useState } from "react"
import Link from "next/link"
import {
  DownloadCloud,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
} from "lucide-react"

import { useConnectors, useIntake } from "@/lib/api/hooks"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

/**
 * Normalize one connector record from `useConnectors()` (untyped
 * `Record<string, unknown>`) into a `{ id, label }` pair. The backend shape is
 * `{ id, name, capabilities, health }`; we fall back through the plausible id
 * fields and skip records with no usable id.
 */
function connectorOption(
  raw: Record<string, unknown>,
): { id: string; label: string } | null {
  const id =
    typeof raw.id === "string"
      ? raw.id
      : typeof raw.connector === "string"
        ? raw.connector
        : typeof raw.name === "string"
          ? raw.name
          : null
  if (!id) return null
  const name = typeof raw.name === "string" && raw.name !== id ? raw.name : null
  return { id, label: name ? `${id} — ${name}` : id }
}

/**
 * "Import patient" surface. Picks a registered connector, takes a
 * source-system patient id (plus an optional local id override), and runs
 * `POST /intake`. On success it reports the resource + hypothesis counts and
 * deep-links to the new patient's AI Review tab.
 *
 * Copy stays associative and factual: intake gathers and connects records for
 * clinician review — it never asserts a diagnosis.
 */
export function IntakePanel() {
  const {
    data: connectors,
    isPending: connectorsPending,
    isError: connectorsError,
  } = useConnectors()
  const intake = useIntake()

  const [connector, setConnector] = useState("")
  const [sourcePatientId, setSourcePatientId] = useState("")
  const [patientIdOverride, setPatientIdOverride] = useState("")

  const options = (connectors ?? [])
    .map(connectorOption)
    .filter((o): o is { id: string; label: string } => o !== null)

  const canSubmit =
    connector.length > 0 && sourcePatientId.trim().length > 0 && !intake.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    const override = patientIdOverride.trim()
    intake.mutate({
      connector,
      source_patient_id: sourcePatientId.trim(),
      ...(override ? { patient_id: override } : {}),
    })
  }

  return (
    <section aria-label="Import patient" className="mf-surface-card p-5">
      <div className="mb-4 flex items-center gap-2.5">
        <div
          className="flex size-9 items-center justify-center rounded-lg bg-[var(--mf-accent-soft)]"
          aria-hidden="true"
        >
          <DownloadCloud className="size-4 text-[var(--mf-accent)]" />
        </div>
        <div>
          <h2 className="mf-display text-lg font-semibold leading-tight">
            Import patient
          </h2>
          <p className="text-xs" style={{ color: "var(--mf-ink-soft)" }}>
            Ingest a record from a connected source for cited review
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="intake-connector">Connector</Label>
          {connectorsError ? (
            <p className="text-xs text-destructive" role="alert">
              Could not load connectors. The backend may be unreachable.
            </p>
          ) : (
            <Select
              value={connector}
              // @base-ui passes string | null — coerce to keep state a string.
              onValueChange={(v) => setConnector(v ?? "")}
              disabled={connectorsPending || options.length === 0}
            >
              <SelectTrigger id="intake-connector" className="w-full">
                <SelectValue
                  placeholder={
                    connectorsPending
                      ? "Loading connectors…"
                      : options.length === 0
                        ? "No connectors registered"
                        : "Select a connector"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {options.map((opt) => (
                  <SelectItem key={opt.id} value={opt.id}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="intake-source-id">Source patient ID</Label>
          <Input
            id="intake-source-id"
            value={sourcePatientId}
            onChange={(e) => setSourcePatientId(e.target.value)}
            placeholder="e.g. DEMO-001"
            autoComplete="off"
          />
          <p className="text-xs" style={{ color: "var(--mf-ink-soft)" }}>
            The patient&apos;s id as known to the selected source connector.
          </p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="intake-override">Local patient ID override</Label>
          <Input
            id="intake-override"
            value={patientIdOverride}
            onChange={(e) => setPatientIdOverride(e.target.value)}
            placeholder="optional — auto-generated if left blank"
            autoComplete="off"
          />
        </div>

        <Button type="submit" disabled={!canSubmit} className="w-full sm:w-auto">
          {intake.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Importing…
            </>
          ) : (
            <>
              <DownloadCloud className="size-4" aria-hidden="true" />
              Import patient
            </>
          )}
        </Button>
      </form>

      {intake.isError && (
        <div
          className="mt-4 flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-4"
          role="alert"
        >
          <AlertTriangle
            className="mt-0.5 size-4 shrink-0 text-destructive"
            aria-hidden="true"
          />
          <div>
            <p className="text-sm font-medium text-foreground">Import failed</p>
            <p className="mt-1 text-xs" style={{ color: "var(--mf-ink-soft)" }}>
              {intake.error instanceof Error
                ? intake.error.message
                : "The import could not be completed."}
            </p>
          </div>
        </div>
      )}

      {intake.isSuccess && intake.data && (
        <div
          className="mt-4 rounded-lg border border-[var(--mf-accent)]/30 bg-[var(--mf-accent-soft)] p-4"
          role="status"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2
              className="size-4 shrink-0 text-success"
              aria-hidden="true"
            />
            <p className="text-sm font-semibold text-foreground">
              Patient imported
            </p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="font-mono">
              {intake.data.patient_id}
            </Badge>
            <Badge variant="secondary">
              {intake.data.resource_count} resources
            </Badge>
            <Badge variant="secondary">
              {(intake.data.hypothesis_ids ?? []).length} hypotheses surfaced
            </Badge>
          </div>
          <p className="mt-3 text-xs" style={{ color: "var(--mf-ink-soft)" }}>
            Surfaced hypotheses are associative and cited — open the review to
            consider each against the source.
          </p>
          <Link
            href={`/patients/${encodeURIComponent(intake.data.patient_id)}/packet`}
            className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--mf-accent)] hover:underline"
          >
            Open AI Review
            <ChevronRight className="size-3.5" aria-hidden="true" />
          </Link>
        </div>
      )}
    </section>
  )
}
