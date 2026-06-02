"use client"

import { useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { MOCK_PROVIDERS } from "@/lib/patient-flow/mock-providers"
import type { AppointmentModality } from "@/lib/patient-flow/types"
import { CARE_CATEGORIES } from "@/lib/patient-flow/intake-questions"
import { useMedFlowStore } from "@/lib/store"

function formatSlot(iso: string) {
  return new Date(iso).toLocaleString("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export default function BookingPage() {
  const router = useRouter()
  const category = useMedFlowStore((s) => s.patientCareCategory)
  const setBooking = useMedFlowStore((s) => s.setPatientBooking)

  const [providerId, setProviderId] = useState(MOCK_PROVIDERS[0]?.id ?? "")
  const [language, setLanguage] = useState<"EN" | "FR" | "ALL">("ALL")
  const [modality, setModality] = useState<AppointmentModality | "ALL">("ALL")
  const [slotId, setSlotId] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)

  const provider = MOCK_PROVIDERS.find((p) => p.id === providerId)

  const filteredSlots = useMemo(() => {
    if (!provider) return []
    return provider.slots.filter((s) => {
      if (modality !== "ALL" && s.modality !== modality) return false
      return true
    })
  }, [provider, modality])

  const categoryLabel =
    CARE_CATEGORIES.find((c) => c.id === category)?.label ?? "Care visit"

  useEffect(() => {
    if (!category) router.replace("/patient/care-select")
  }, [category, router])

  if (!category || !provider) return null

  function handleConfirm() {
    if (!slotId || !category) return
    setBooking({ providerId, slotId, careCategory: category })
    router.push("/patient/confirmation")
  }

  if (confirming && slotId) {
    const slot = provider.slots.find((s) => s.id === slotId)
    return (
      <div className="space-y-6">
        <h1 className="mf-display text-2xl font-semibold">Review your booking</h1>
        <div
          className="rounded-xl border-2 p-5 space-y-3"
          style={{ borderColor: "var(--mf-ink)" }}
        >
          <p className="font-semibold">{provider.name}</p>
          <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            {provider.credential}
          </p>
          {slot && (
            <>
              <p className="text-sm">{formatSlot(slot.start)}</p>
              <span
                className="inline-block rounded-full px-3 py-1 text-xs font-semibold capitalize"
                style={{ background: "var(--mf-accent-soft)" }}
              >
                {slot.modality}
              </span>
            </>
          )}
          <p className="text-sm">{categoryLabel}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button type="button" className="mf-btn-secondary flex-1" onClick={() => setConfirming(false)}>
            Go back
          </button>
          <button type="button" className="mf-btn-primary flex-1" onClick={handleConfirm}>
            Confirm appointment
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="mf-eyebrow mb-2">Step 3</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          Pick a time that works for you
        </h1>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="text-sm font-medium">
          Provider
          <select
            className="mt-1 block w-full min-h-[44px] rounded-lg border-2 px-3"
            style={{ borderColor: "var(--mf-ink)" }}
            value={providerId}
            onChange={(e) => {
              setProviderId(e.target.value)
              setSlotId(null)
            }}
          >
            {MOCK_PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          Language
          <select
            className="mt-1 block min-h-[44px] rounded-lg border-2 px-3"
            style={{ borderColor: "var(--mf-ink)" }}
            value={language}
            onChange={(e) => setLanguage(e.target.value as "EN" | "FR" | "ALL")}
          >
            <option value="ALL">Any</option>
            <option value="EN">English</option>
            <option value="FR">French</option>
          </select>
        </label>
        <label className="text-sm font-medium">
          Modality
          <select
            className="mt-1 block min-h-[44px] rounded-lg border-2 px-3"
            style={{ borderColor: "var(--mf-ink)" }}
            value={modality}
            onChange={(e) =>
              setModality(e.target.value as AppointmentModality | "ALL")
            }
          >
            <option value="ALL">Any</option>
            <option value="video">Video</option>
            <option value="phone">Phone</option>
            <option value="in-person">In-person</option>
          </select>
        </label>
      </div>

      <div
        className="rounded-xl border-2 p-5"
        style={{ borderColor: "var(--mf-patient-line)", background: "var(--mf-patient)" }}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="mf-display text-lg font-semibold">{provider.name}</p>
            <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
              {provider.credential}
            </p>
            <p className="mt-2 text-sm">{provider.bio}</p>
          </div>
          <span
            className="shrink-0 rounded-full px-2 py-1 text-xs font-semibold"
            style={{ background: "var(--mf-success)", color: "#fff" }}
          >
            Available
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">Available times</h2>
        <ul className="space-y-2" role="list">
          {filteredSlots.map((slot) => (
            <li key={slot.id}>
              <button
                type="button"
                data-selected={slotId === slot.id}
                className="mf-card-selectable w-full flex items-center justify-between px-4 py-3"
                onClick={() => setSlotId(slot.id)}
                aria-pressed={slotId === slot.id}
              >
                <span>{formatSlot(slot.start)}</span>
                <span className="text-xs font-semibold capitalize">{slot.modality}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <button
        type="button"
        disabled={!slotId}
        className="mf-btn-primary w-full"
        onClick={() => setConfirming(true)}
      >
        Continue
      </button>
    </div>
  )
}
