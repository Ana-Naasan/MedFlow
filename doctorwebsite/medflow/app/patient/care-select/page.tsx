"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { Brain, Briefcase, Heart, Stethoscope, type LucideIcon } from "lucide-react"
import {
  CARE_CATEGORIES,
  type CareCategoryIconKey,
} from "@/lib/patient-flow/intake-questions"
import type { CareCategoryId } from "@/lib/patient-flow/types"
import { useMedFlowStore } from "@/lib/store"

const CARE_ICONS: Record<CareCategoryIconKey, LucideIcon> = {
  brain: Brain,
  stethoscope: Stethoscope,
  heart: Heart,
  briefcase: Briefcase,
}

export default function CareSelectPage() {
  const router = useRouter()
  const setCategory = useMedFlowStore((s) => s.setPatientCareCategory)
  const stored = useMedFlowStore((s) => s.patientCareCategory)
  const [selected, setSelected] = useState<CareCategoryId | null>(stored)

  function handleContinue() {
    if (!selected) return
    setCategory(selected)
    router.push("/patient/intake")
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="mf-eyebrow mb-2">Step 1</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          What kind of support are you looking for?
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          Choose one - we&apos;ll tailor the next few questions to you.
        </p>
      </div>

      <div className="grid gap-[18px] sm:grid-cols-2" role="listbox" aria-label="Care categories">
        {CARE_CATEGORIES.map(({ id, label, subtitle, iconKey }) => {
          const Icon = CARE_ICONS[iconKey]
          return (
            <button
              key={id}
              type="button"
              role="option"
              aria-selected={selected === id}
              data-selected={selected === id}
              className="mf-card-selectable flex flex-col gap-2 p-5"
              onClick={() => setSelected(id)}
            >
              <Icon
                className="size-7 text-[var(--mf-accent)]"
                strokeWidth={1.75}
                aria-hidden
              />
              <span className="mf-display text-lg font-semibold">{label}</span>
              <span className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                {subtitle}
              </span>
            </button>
          )
        })}
      </div>

      <button
        type="button"
        disabled={!selected}
        onClick={handleContinue}
        className="mf-btn-primary w-full sm:w-auto"
      >
        Continue
      </button>
    </div>
  )
}
