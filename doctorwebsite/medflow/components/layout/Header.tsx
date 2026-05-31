"use client"

import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { ChevronRight } from "lucide-react"
import { NotificationsMenu } from "@/components/layout/NotificationsMenu"

const ROUTE_LABELS: Readonly<Record<string, string>> = {
  dashboard: "Records",
  patients: "Patients",
  profile: "Profile",
  investigations: "Investigations",
  encounters: "Encounters",
  notes: "Notes",
  billing: "Billing",
  files: "Files",
  edocuments: "eDocuments",
  scheduler: "Scheduler",
  directory: "Directory",
  memos: "Memos",
  tasks: "Tasks",
  utilities: "Utilities",
} as const

function humanizeSegment(segment: string): string {
  if (/^\d+$/.test(segment)) return `#${segment}`
  return ROUTE_LABELS[segment] ?? segment.charAt(0).toUpperCase() + segment.slice(1)
}

interface BreadcrumbSegment {
  label: string
  isLast: boolean
}

function parseBreadcrumbs(pathname: string): BreadcrumbSegment[] {
  if (pathname === "/dashboard") {
    return [{ label: "Records", isLast: true }]
  }

  const segments = pathname.split("/").filter(Boolean)
  return segments.map((seg, idx) => ({
    label: humanizeSegment(seg),
    isLast: idx === segments.length - 1,
  }))
}

function formatClock(date: Date): string {
  const hours = date.getHours()
  const minutes = date.getMinutes().toString().padStart(2, "0")
  const ampm = hours >= 12 ? "PM" : "AM"
  const displayHour = hours % 12 === 0 ? 12 : hours % 12

  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ]

  return `${displayHour}:${minutes} ${ampm} ${days[date.getDay()]}, ${months[date.getMonth()]} ${date.getDate()}`
}

export function Header() {
  const pathname = usePathname()
  const [clock, setClock] = useState<string>("")

  useEffect(() => {
    setClock(formatClock(new Date()))
    const id = setInterval(() => setClock(formatClock(new Date())), 60_000)
    return () => clearInterval(id)
  }, [])

  const breadcrumbs = parseBreadcrumbs(pathname)

  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between gap-4 border-b-2 px-4 sm:px-6"
      style={{
        background: "var(--mf-paper)",
        borderColor: "var(--mf-ink)",
      }}
    >
      <nav aria-label="Breadcrumb">
        <ol className="mf-display flex items-center gap-1.5 text-sm" role="list">
          {breadcrumbs.map((crumb, idx) => (
            <li key={idx} className="flex items-center gap-1.5">
              {idx > 0 && (
                <ChevronRight
                  className="size-3.5"
                  style={{ color: "var(--mf-ink-soft)" }}
                  aria-hidden="true"
                />
              )}
              <span
                className={crumb.isLast ? "font-semibold" : ""}
                style={{
                  color: crumb.isLast ? "var(--mf-ink)" : "var(--mf-ink-soft)",
                }}
                aria-current={crumb.isLast ? "page" : undefined}
              >
                {crumb.label}
              </span>
            </li>
          ))}
        </ol>
      </nav>

      <div className="flex items-center gap-4">
        <time
          className="mf-eyebrow !text-[10px] hidden sm:block"
          role="status"
          aria-live="polite"
        >
          {clock}
        </time>
        <NotificationsMenu />
      </div>
    </header>
  )
}
