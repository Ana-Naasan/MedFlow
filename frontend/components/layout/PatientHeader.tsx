"use client"

import { FileText, Tag, Scissors, CheckSquare, StickyNote } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import type { Patient } from "@/lib/types"

interface PatientHeaderProps {
  patient: Patient
}

function calculateAge(dob: string): number {
  return Math.floor(
    (Date.now() - new Date(dob).getTime()) / (1000 * 60 * 60 * 24 * 365.25)
  )
}

function formatDOB(dob: string): string {
  return new Date(dob).toLocaleDateString("en-CA", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

function MetaDivider() {
  return (
    <span
      className="hidden h-3 w-px shrink-0 sm:inline-block"
      style={{ background: "var(--mf-ink)", opacity: 0.2 }}
      aria-hidden="true"
    />
  )
}

function PatientIdBlock({ patient }: { patient: Patient }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-1 text-center"
      style={{ color: "var(--mf-ink-soft)" }}
    >
      <span className="font-mono text-sm font-semibold tabular-nums text-[var(--mf-ink)] sm:text-base">
        ID: {patient.id}
      </span>
      <span className="text-sm leading-snug sm:text-base">{patient.location}</span>
    </div>
  )
}

const QUICK_ACTIONS = [
  { label: "Env", icon: FileText, ariaLabel: "Add envelope" },
  { label: "Label", icon: Tag, ariaLabel: "Add label" },
  { label: "OR", icon: Scissors, ariaLabel: "Add OR booking" },
  { label: "Task", icon: CheckSquare, ariaLabel: "Add task" },
  { label: "Memo", icon: StickyNote, ariaLabel: "Add memo" },
] as const

export function PatientHeader({ patient }: PatientHeaderProps) {
  // A backend-only patient (not in the mock EMR) has no DOB — show "—" rather than
  // rendering "NaN yrs" / "Invalid Date".
  const hasDob = Boolean(patient.dob) && !Number.isNaN(new Date(patient.dob).getTime())
  const age = hasDob ? calculateAge(patient.dob) : null
  const initials = `${patient.name.first.charAt(0)}${patient.name.last.charAt(0)}`
  const fullNameLastFirst = `${patient.name.last}, ${patient.name.first}`

  return (
    <header
      className="shrink-0 border-b-2 py-5"
      style={{
        borderColor: "var(--mf-ink)",
        background: "var(--mf-paper)",
      }}
      aria-label="Patient information"
    >
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6">
        {/*
          Three-zone grid: equal side columns center the ID block in the header.
          (ui-ux-pro-max: visual hierarchy, spacing scale, whitespace balance)
        */}
        <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:gap-8">
          {/* Zone 1 — patient identity */}
          <div className="flex min-w-0 items-center gap-5 lg:justify-self-start">
            <Avatar className="size-12 shrink-0 self-center sm:size-14">
              <AvatarFallback
                className="text-base font-semibold sm:text-lg"
                style={{
                  background: "var(--mf-clinician)",
                  color: "var(--mf-accent)",
                }}
              >
                {initials}
              </AvatarFallback>
            </Avatar>

            <div className="flex min-w-0 flex-col justify-center gap-2">
              <div className="min-w-0">
                <span className="mf-eyebrow mb-1 block text-xs">Patient</span>
                <h1 className="mf-display truncate text-xl font-semibold leading-tight text-[var(--mf-ink)] sm:text-2xl">
                  {fullNameLastFirst}
                </h1>
              </div>

              <p
                className="text-sm leading-relaxed sm:text-base"
                style={{ color: "var(--mf-ink-soft)" }}
              >
                {hasDob ? `${formatDOB(patient.dob)} · ${age} yrs · ` : ""}
                {capitalize(patient.sex)}
              </p>

              <div
                className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm leading-relaxed sm:gap-x-4 sm:text-base"
                style={{ color: "var(--mf-ink-soft)" }}
              >
                <span>
                  <span className="font-semibold text-[var(--mf-ink)]">PHN:</span>{" "}
                  <span className="tabular-nums">{patient.healthNumber || "-"}</span>
                </span>
                <MetaDivider />
                <span>
                  <span className="font-semibold text-[var(--mf-ink)]">Family:</span>{" "}
                  {patient.familyPhysician ?? "-"}
                </span>
                <MetaDivider />
                <span>
                  <span className="font-semibold text-[var(--mf-ink)]">Primary:</span>{" "}
                  Dr. {patient.primaryPhysician}
                </span>
              </div>
            </div>
          </div>

          {/* Zone 2 — ID (true horizontal center on desktop) */}
          <div
            className="hidden min-w-[120px] flex-col items-center justify-center px-6 lg:flex lg:px-10"
            style={{
              borderLeft: "1px solid color-mix(in srgb, var(--mf-ink) 15%, transparent)",
              borderRight: "1px solid color-mix(in srgb, var(--mf-ink) 15%, transparent)",
            }}
          >
            <PatientIdBlock patient={patient} />
          </div>

          {/* Zone 3 — mobile ID + quick actions */}
          <div className="flex flex-col items-center gap-4 lg:flex-row lg:items-center lg:justify-end lg:justify-self-end lg:gap-2">
            <div className="lg:hidden">
              <PatientIdBlock patient={patient} />
            </div>

            <div
              className="flex flex-wrap items-center justify-center gap-2 lg:justify-end"
              role="group"
              aria-label="Quick actions"
            >
              {QUICK_ACTIONS.map(({ label, icon: Icon, ariaLabel }) => (
                <Button
                  key={label}
                  variant="outline"
                  size="sm"
                  className="h-10 min-h-[44px] px-3 text-sm"
                  aria-label={ariaLabel}
                >
                  <Icon className="size-4 shrink-0" aria-hidden="true" />
                  <span className="ml-1.5">{label}</span>
                </Button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
