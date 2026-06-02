"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { CheckCircle2 } from "lucide-react"
import { getProvider } from "@/lib/patient-flow/mock-providers"
import { CARE_CATEGORIES } from "@/lib/patient-flow/intake-questions"
import { useMedFlowStore } from "@/lib/store"

export default function ConfirmationPage() {
  const router = useRouter()
  const booking = useMedFlowStore((s) => s.patientBooking)

  useEffect(() => {
    if (!booking) router.replace("/patient/booking")
  }, [booking, router])

  if (!booking) return null

  const provider = getProvider(booking.providerId)
  const slot = provider?.slots.find((s) => s.id === booking.slotId)
  const categoryLabel =
    CARE_CATEGORIES.find((c) => c.id === booking.careCategory)?.label ?? "Visit"

  return (
    <div className="space-y-8 text-center">
      <div className="flex flex-col items-center gap-3">
        <CheckCircle2
          className="size-14"
          style={{ color: "var(--mf-success)" }}
          aria-hidden="true"
        />
        <h1 className="mf-display text-[32px] font-semibold">
          You&apos;re all set
        </h1>
        <p style={{ color: "var(--mf-ink-soft)" }}>
          We&apos;ve saved your appointment. You&apos;ll get a reminder before
          your visit.
        </p>
      </div>

      <div
        className="rounded-xl border-2 p-5 text-left"
        style={{ borderColor: "var(--mf-ink)" }}
      >
        <p className="font-semibold">{provider?.name}</p>
        <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          {provider?.credential}
        </p>
        {slot && (
          <p className="mt-3 text-sm">
            {new Date(slot.start).toLocaleString("en-CA", {
              weekday: "long",
              month: "long",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
              timeZoneName: "short",
            })}
          </p>
        )}
        <p className="mt-2 text-sm capitalize">{slot?.modality} visit</p>
        <p className="mt-1 text-sm">{categoryLabel}</p>
      </div>

      <div className="flex flex-col gap-3">
        <button type="button" className="mf-btn-secondary w-full">
          Add to calendar
        </button>
        <button type="button" className="mf-btn-secondary w-full">
          Message provider
        </button>
        <Link href="/patient/dashboard" className="mf-btn-primary w-full text-center">
          View dashboard
        </Link>
      </div>
    </div>
  )
}
