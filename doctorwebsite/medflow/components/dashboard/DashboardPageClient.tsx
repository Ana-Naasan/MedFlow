"use client"

import Link from "next/link"
import { MapPin } from "lucide-react"
import { useMedFlowStore } from "@/lib/store"
import type { Patient } from "@/lib/types"

interface DashboardPageClientProps {
  allPatients: Patient[]
}

function getAge(dob: string): number {
  const birth = new Date(dob)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
  return age
}

function getInitials(first: string, last: string): string {
  return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase()
}

export function DashboardPageClient({ allPatients }: DashboardPageClientProps) {
  const recentPatientIds = useMedFlowStore((s) => s.recentPatientIds)

  const recentPatients = recentPatientIds
    .map((id) => allPatients.find((p) => p.id === id))
    .filter((p): p is Patient => p !== undefined)

  if (recentPatients.length === 0) {
    return (
      <p
        className="mf-surface-card p-6 text-sm"
        style={{ color: "var(--mf-ink-soft)" }}
      >
        No recently accessed patients. Use the patient search to open a chart.
      </p>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {recentPatients.map((patient) => {
        const fullName = `${patient.name.first} ${patient.name.last}`
        const age = getAge(patient.dob)
        const primaryCondition = patient.problems.find((p) => p.status === "active")?.description

        return (
          <Link
            key={patient.id}
            href={`/patients/${patient.id}/profile`}
            className="mf-surface-card group block p-5 transition-shadow duration-150 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
            aria-label={`Open chart for ${fullName}`}
          >
            <div className="flex items-start gap-3">
              {/* Avatar initials */}
              <div
                className="flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold"
                style={{
                  background: "var(--mf-clinician)",
                  color: "var(--mf-accent)",
                }}
                aria-hidden="true"
              >
                {getInitials(patient.name.first, patient.name.last)}
              </div>

              <div className="min-w-0 flex-1">
                <p
                  className="mf-display truncate text-sm font-semibold transition-colors group-hover:opacity-80"
                  style={{ color: "var(--mf-ink)" }}
                >
                  {fullName}
                </p>
                <p className="text-xs" style={{ color: "var(--mf-ink-soft)" }}>
                  {age} years old · {patient.sex.charAt(0).toUpperCase() + patient.sex.slice(1)}
                </p>
              </div>
            </div>

            {primaryCondition && (
              <p className="mt-3 truncate text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Primary: </span>
                {primaryCondition}
              </p>
            )}

            {patient.location && (
              <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="size-3 shrink-0" aria-hidden="true" />
                <span className="truncate">{patient.location}</span>
              </div>
            )}
          </Link>
        )
      })}
    </div>
  )
}
