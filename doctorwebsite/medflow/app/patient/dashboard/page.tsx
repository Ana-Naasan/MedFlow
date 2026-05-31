"use client"

import Link from "next/link"
import { useSession } from "next-auth/react"
import { Calendar, FileText, MessageCircle } from "lucide-react"
import { getProvider } from "@/lib/patient-flow/mock-providers"
import { CARE_CATEGORIES } from "@/lib/patient-flow/intake-questions"
import { useMedFlowStore } from "@/lib/store"

export default function PatientDashboardPage() {
  const { data: session } = useSession()
  const booking = useMedFlowStore((s) => s.patientBooking)
  const provider = booking ? getProvider(booking.providerId) : null
  const slot = provider?.slots.find((s) => s.id === booking?.slotId)
  const categoryLabel = booking
    ? CARE_CATEGORIES.find((c) => c.id === booking.careCategory)?.label
    : null

  return (
    <div className="space-y-8">
      <div>
        <p className="mf-eyebrow mb-2">Your dashboard</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          Hi{session?.user?.name ? `, ${session.user.name.split(" ")[0]}` : ""}
        </h1>
        <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          Here&apos;s what&apos;s coming up for your care.
        </p>
      </div>

      {booking && slot ? (
        <div
          className="rounded-xl border-2 p-5"
          style={{ borderColor: "var(--mf-accent)", background: "var(--mf-accent-soft)" }}
        >
          <div className="flex items-start gap-3">
            <Calendar className="size-5 shrink-0" style={{ color: "var(--mf-accent)" }} aria-hidden="true" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--mf-accent)" }}>
                Upcoming
              </p>
              <p className="mf-display mt-1 text-lg font-semibold">{categoryLabel}</p>
              <p className="text-sm mt-1">
                {new Date(slot.start).toLocaleString("en-CA", {
                  weekday: "long",
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </p>
              <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                with {provider?.name}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="rounded-xl border-2 border-dashed p-6 text-center"
          style={{ borderColor: "var(--mf-ink-soft)" }}
        >
          <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            No upcoming visits yet.
          </p>
          <Link href="/patient/care-select" className="mf-btn-primary mt-4 inline-flex">
            Book care
          </Link>
        </div>
      )}

      <div className="grid gap-[18px] sm:grid-cols-2">
        <Link
          href="/patient/care-plan"
          className="mf-card-selectable flex flex-col gap-2 p-5 no-underline"
          style={{ color: "inherit" }}
        >
          <FileText className="size-5" aria-hidden="true" />
          <span className="font-semibold">Care plan</span>
          <span className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            Notes, next steps, and follow-up
          </span>
        </Link>
        <div className="mf-card-selectable flex flex-col gap-2 p-5 opacity-90">
          <MessageCircle className="size-5" aria-hidden="true" />
          <span className="font-semibold">Messages</span>
          <span className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            Chat with your care team
          </span>
        </div>
      </div>
    </div>
  )
}
