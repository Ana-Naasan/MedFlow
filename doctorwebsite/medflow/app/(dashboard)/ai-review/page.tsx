"use client"

import { BackendPatientList } from "@/components/ai-review/BackendPatientList"
import { IntakePanel } from "@/components/ai-review/IntakePanel"

/**
 * AI Review entry point. Lists real backend patients (each row links into its
 * cited decision packet) and provides the connector-driven intake flow to
 * ingest new ones. This is the bridge between MedFlow's chart UI and the
 * decision-support backend; it does not touch the mock directory.
 */
export default function AIReviewPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="space-y-1">
        <p className="mf-eyebrow mb-1">Decision support</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          AI Review
        </h1>
        <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          Review cited polypharmacy hypotheses for backend patients, or import a
          new record from a connected source. The AI gathers and connects; the
          clinician decides.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
        <BackendPatientList />
        <IntakePanel />
      </div>
    </div>
  )
}
