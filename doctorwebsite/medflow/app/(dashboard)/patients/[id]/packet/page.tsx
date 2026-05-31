"use client"

import { useMemo, useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import { Inbox, Loader2, Sparkles } from "lucide-react"

import { BackendPatientSelect } from "@/components/packet/BackendPatientSelect"
import { CompletenessIndicator } from "@/components/packet/CompletenessIndicator"
import { DataGapsBanner } from "@/components/packet/DataGapsBanner"
import { HypothesisCard } from "@/components/packet/HypothesisCard"
import { PacketLoadFailurePanel } from "@/components/packet/PacketLoadFailurePanel"
import { PacketSummary } from "@/components/packet/PacketSummary"
import {
  PacketLoadError,
  usePacket,
  usePatients,
} from "@/lib/api/hooks"
import type { DecisionPacket } from "@/lib/api/types"

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] },
  },
}

export default function PacketPage() {
  // The route id is a MedFlow MOCK id — it almost certainly does not exist in
  // the backend. We use it only as a default-selection hint.
  const { id: routeId } = useParams<{ id: string }>()

  const {
    data: patientIds,
    isLoading: patientsLoading,
    isError: patientsError,
    error: patientsErr,
  } = usePatients()

  // The operator's explicit override of the backend patient (null = use default).
  const [override, setOverride] = useState<string | null>(null)

  const ids = patientIds ?? []
  const routeInBackend = ids.includes(routeId)

  // Active backend patient id: explicit override → route id if backend knows it
  // → first backend patient → "" (no backend patients).
  const activePatientId = useMemo(() => {
    if (override && ids.includes(override)) return override
    if (routeInBackend) return routeId
    return ids[0] ?? ""
  }, [override, ids, routeInBackend, routeId])

  const hasBackendPatient = activePatientId.length > 0

  const {
    data: packet,
    isLoading: packetLoading,
    isError: packetIsError,
    error: packetError,
  } = usePacket(activePatientId, hasBackendPatient)

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      className="mx-auto max-w-5xl space-y-5"
    >
      <header className="flex items-start gap-2.5">
        <Sparkles
          size={20}
          className="mt-0.5 shrink-0 text-[var(--accent)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-lg font-semibold text-foreground">AI Review</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Cited, source-derived hypotheses for review. The AI gathers and
            connects; the clinician decides.
          </p>
        </div>
      </header>

      {/* Backend-patient reconciliation selector */}
      {patientsLoading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Loading backend patients…
        </div>
      ) : patientsError ? (
        <div
          role="alert"
          className="rounded-lg border border-[color-mix(in_oklch,var(--danger)_28%,transparent)] bg-[color-mix(in_oklch,var(--danger)_8%,transparent)] p-4 text-sm text-foreground"
        >
          Could not reach the backend to list patients.
          {patientsErr instanceof Error && (
            <span className="text-[var(--text-secondary)]">
              {" "}
              {patientsErr.message}
            </span>
          )}
        </div>
      ) : ids.length === 0 ? (
        <EmptyBackend />
      ) : (
        <div className="rounded-lg border border-border bg-bg-surface p-4">
          <BackendPatientSelect
            patientIds={ids}
            value={activePatientId}
            onChange={setOverride}
            matchedRoute={routeInBackend}
          />
        </div>
      )}

      {/* Packet body */}
      {hasBackendPatient && (
        <PacketBody
          loading={packetLoading}
          isError={packetIsError}
          error={packetError}
          packet={packet}
        />
      )}
    </motion.div>
  )
}

function EmptyBackend() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border bg-bg-surface px-6 py-12 text-center">
      <Inbox size={28} className="text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium text-foreground">
        No backend patients found.
      </p>
      <p className="max-w-sm text-sm text-[var(--text-secondary)]">
        Run an intake to ingest a patient from a connector before an AI review
        packet can be generated.
      </p>
    </div>
  )
}

interface PacketBodyProps {
  loading: boolean
  isError: boolean
  error: PacketLoadError | null
  packet: DecisionPacket | undefined
}

function PacketBody({ loading, isError, error, packet }: PacketBodyProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-bg-surface p-6 text-sm text-muted-foreground">
        <Loader2 size={16} className="animate-spin" aria-hidden="true" />
        Generating decision packet… this may take several seconds on a cold
        cache.
      </div>
    )
  }

  if (isError || !packet) {
    // PacketLoadError carries the diagnostic; a missing-packet fall-through
    // still gets a panel so the operator never sees a blank page.
    const diag =
      error instanceof PacketLoadError
        ? error.diag
        : { status: undefined, body: null, url: "", elapsedMs: 0 }
    return <PacketLoadFailurePanel diag={diag} />
  }

  const completeness = packet.completeness ?? []
  const dataGaps = packet.data_gaps ?? []
  // INVARIANT: a hypothesis with zero resolvable citations must NOT be shown.
  const hypotheses = (packet.hypotheses ?? []).filter(
    (h) => Array.isArray(h.citations) && h.citations.length > 0,
  )

  return (
    <div className="space-y-5">
      {packet.cache_status && (
        <p className="text-xs text-[var(--text-muted)]">
          Cache: {packet.cache_status}
        </p>
      )}

      <DataGapsBanner gaps={dataGaps} />

      {packet.summary_markdown && (
        <PacketSummary markdown={packet.summary_markdown} />
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_320px]">
        <section aria-label="Differential" className="space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Differential ({hypotheses.length})
          </h2>
          {hypotheses.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-bg-surface px-6 py-10 text-center text-sm text-[var(--text-secondary)]">
              No cited hypotheses to review. A claim without a resolvable
              citation is not shown.
            </div>
          ) : (
            hypotheses.map((hypothesis) => (
              <HypothesisCard key={hypothesis.id} hypothesis={hypothesis} />
            ))
          )}
        </section>

        <aside className="space-y-5">
          <CompletenessIndicator completeness={completeness} />
        </aside>
      </div>
    </div>
  )
}
