"use client"

import { useCallback, useMemo, useState, type ReactNode } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import { Inbox, Loader2, Sparkles } from "lucide-react"

import { BackendPatientSelect } from "@/components/packet/BackendPatientSelect"
import { CitationChip } from "@/components/packet/CitationChip"
import { CompletenessIndicator } from "@/components/packet/CompletenessIndicator"
import { DataGapsBanner } from "@/components/packet/DataGapsBanner"
import { EvidenceDrawer } from "@/components/packet/EvidenceDrawer"
import { HypothesisActions } from "@/components/packet/HypothesisActions"
import { HypothesisCard } from "@/components/packet/HypothesisCard"
import { PacketLoadFailurePanel } from "@/components/packet/PacketLoadFailurePanel"
import { PacketSummary } from "@/components/packet/PacketSummary"
import { useKeyboardReview } from "@/components/packet/useKeyboardReview"
import {
  PacketLoadError,
  useConfirmHypothesis,
  useDismissHypothesis,
  usePacket,
  usePatients,
} from "@/lib/api/hooks"
import type { Citation, DecisionPacket, Hypothesis } from "@/lib/api/types"

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
          patientId={activePatientId}
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
  /** Backend patient id — threaded down for confirm/dismiss + resource resolution. */
  patientId: string
  loading: boolean
  isError: boolean
  error: PacketLoadError | null
  packet: DecisionPacket | undefined
}

function PacketBody({
  patientId,
  loading,
  isError,
  error,
  packet,
}: PacketBodyProps) {
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

  // The success branch is delegated so that the drawer/keyboard/mutation hooks
  // live in a component that is only mounted once the packet has resolved —
  // PacketBody itself stays hook-free above its conditional returns.
  return <PacketDifferential patientId={patientId} packet={packet} />
}

interface PacketDifferentialProps {
  patientId: string
  packet: DecisionPacket
}

/**
 * The resolved differential: cited hypotheses with interactive citation chips
 * + confirm/dismiss actions, a single shared evidence drawer, and keyboard
 * review wiring. Mounted only when the packet has loaded.
 */
function PacketDifferential({ patientId, packet }: PacketDifferentialProps) {
  const completeness = packet.completeness ?? []
  const dataGaps = packet.data_gaps ?? []
  // INVARIANT: a hypothesis with zero resolvable citations must NOT be shown.
  const hypotheses = useMemo(
    () =>
      (packet.hypotheses ?? []).filter(
        (h) => Array.isArray(h.citations) && h.citations.length > 0,
      ),
    [packet.hypotheses],
  )

  // The single active citation drives the one shared EvidenceDrawer.
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const openCitation = useCallback((citation: Citation) => {
    setActiveCitation(citation)
    setDrawerOpen(true)
  }, [])

  const handleOpenChange = useCallback((open: boolean) => {
    setDrawerOpen(open)
    // Clear the resolved citation once the close animation has handed back.
    if (!open) setActiveCitation(null)
  }, [])

  // Keyboard review fires its own mutation instances (the action buttons have
  // theirs); both invalidate the same packet query on success.
  const confirm = useConfirmHypothesis()
  const dismiss = useDismissHypothesis()

  const openPrimaryCitation = useCallback(
    (hypothesis: Hypothesis) => {
      const primary = hypothesis.citations?.[0]
      if (primary) openCitation(primary)
    },
    [openCitation],
  )

  useKeyboardReview(hypotheses, {
    onConfirm: (id) => confirm.mutate({ id, patientId }),
    onDismiss: (id) => dismiss.mutate({ id, patientId }),
    onOpenPrimaryCitation: openPrimaryCitation,
    onCloseDrawer: () => handleOpenChange(false),
    drawerOpen,
  })

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
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Differential ({hypotheses.length})
            </h2>
            {hypotheses.length > 0 && <KeyboardHint />}
          </div>
          {hypotheses.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border bg-bg-surface px-6 py-10 text-center text-sm text-[var(--text-secondary)]">
              No cited hypotheses to review. A claim without a resolvable
              citation is not shown.
            </div>
          ) : (
            hypotheses.map((hypothesis) => (
              <HypothesisCard
                key={hypothesis.id}
                hypothesis={hypothesis}
                citations={hypothesis.citations.map((citation, i) => (
                  <CitationChip
                    key={`${citation.kind}:${citation.ref}:${i}`}
                    citation={citation}
                    onOpen={openCitation}
                  />
                ))}
                actions={
                  <HypothesisActions
                    hypothesis={hypothesis}
                    patientId={patientId}
                  />
                }
              />
            ))
          )}
        </section>

        <aside className="space-y-5">
          <CompletenessIndicator completeness={completeness} />
        </aside>
      </div>

      {/* One shared drawer resolves whichever citation is active. */}
      <EvidenceDrawer
        citation={activeCitation}
        patientId={patientId}
        open={drawerOpen}
        onOpenChange={handleOpenChange}
      />
    </div>
  )
}

/** Compact, non-intrusive hint listing the review keyboard shortcuts. */
function KeyboardHint() {
  return (
    <p className="hidden items-center gap-1.5 text-[11px] text-[var(--text-muted)] sm:flex">
      <Kbd>j</Kbd>
      <Kbd>k</Kbd>
      move ·<Kbd>c</Kbd>ack ·<Kbd>d</Kbd>dismiss ·<Kbd>↵</Kbd>cite ·
      <Kbd>esc</Kbd>close
    </p>
  )
}

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-border bg-bg-subtle px-1 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">
      {children}
    </kbd>
  )
}
