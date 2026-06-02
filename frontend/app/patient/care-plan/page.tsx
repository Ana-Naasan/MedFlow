"use client"

import Link from "next/link"
import { useMedFlowStore } from "@/lib/store"
import { Check } from "lucide-react"

const NEXT_STEPS = [
  "Try a 5-minute breathing exercise before bed",
  "Keep a short mood note once a day this week",
  "Reach out in messages if symptoms feel worse",
] as const

const MESSAGES = [
  {
    from: "provider",
    text: "Great speaking with you today. Remember you can message us anytime between visits.",
    time: "Yesterday, 4:20 PM",
  },
  {
    from: "patient",
    text: "Thank you — the resources you shared were really helpful.",
    time: "Yesterday, 4:35 PM",
  },
] as const

export default function CarePlanPage() {
  const category = useMedFlowStore((s) => s.patientCareCategory)
  const showWellness =
    category === "mental-health" || category === "wellness"

  return (
    <div className="space-y-10">
      <div>
        <p className="mf-eyebrow mb-2">Your care plan</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          What happens next
        </h1>
      </div>

      <section className="space-y-3" aria-labelledby="summary-heading">
        <h2 id="summary-heading" className="mf-display text-xl font-semibold">
          Provider summary
        </h2>
        <div
          className="rounded-xl border-2 p-5 text-sm leading-relaxed"
          style={{ borderColor: "var(--mf-ink)" }}
        >
          <p>
            You shared that stress and sleep have been weighing on you lately.
            We talked about practical steps you can try this week, and when it
            makes sense to check back in. You&apos;re not alone in this — small
            changes can add up.
          </p>
        </div>
      </section>

      <section className="space-y-3" aria-labelledby="steps-heading">
        <h2 id="steps-heading" className="mf-display text-xl font-semibold">
          Next steps
        </h2>
        <ul className="space-y-2">
          {NEXT_STEPS.map((step) => (
            <li
              key={step}
              className="flex items-start gap-3 rounded-lg border-2 px-4 py-3"
              style={{ borderColor: "var(--mf-paper-2)" }}
            >
              <span
                className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded border-2"
                style={{ borderColor: "var(--mf-accent)" }}
                aria-hidden="true"
              >
                <Check className="size-3" style={{ color: "var(--mf-accent)" }} />
              </span>
              <span className="text-sm">{step}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3" aria-labelledby="followup-heading">
        <h2 id="followup-heading" className="mf-display text-xl font-semibold">
          Follow-up appointment
        </h2>
        <div
          className="rounded-xl p-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          style={{ background: "var(--mf-clinician)", border: "2px solid var(--mf-clinician-line)" }}
        >
          <p className="text-sm">No follow-up scheduled yet.</p>
          <Link href="/patient/booking" className="mf-btn-primary text-sm">
            Book follow-up
          </Link>
        </div>
      </section>

      <section className="space-y-3" aria-labelledby="messages-heading">
        <h2 id="messages-heading" className="mf-display text-xl font-semibold">
          Messages
        </h2>
        <div className="space-y-3">
          {MESSAGES.map((m, i) => (
            <div
              key={i}
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${
                m.from === "patient" ? "ml-auto" : ""
              }`}
              style={{
                background:
                  m.from === "patient"
                    ? "var(--mf-accent-soft)"
                    : "var(--mf-paper-2)",
                border: "2px solid var(--mf-paper-2)",
              }}
            >
              <p>{m.text}</p>
              <p className="mt-1 text-xs" style={{ color: "var(--mf-ink-soft)" }}>
                {m.time}
              </p>
            </div>
          ))}
        </div>
      </section>

      {showWellness && (
        <section className="space-y-3" aria-labelledby="wellness-heading">
          <h2 id="wellness-heading" className="mf-display text-xl font-semibold">
            Wellness tracker
          </h2>
          <div
            className="rounded-xl border-2 p-5"
            style={{ borderColor: "var(--mf-patient-line)", background: "var(--mf-warm-tint)" }}
          >
            <p className="text-sm font-medium mb-3">How are you feeling today?</p>
            <div className="flex flex-wrap gap-2">
              {["Great", "Okay", "Low", "Stressed"].map((mood) => (
                <button key={mood} type="button" className="mf-chip text-sm">
                  {mood}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
