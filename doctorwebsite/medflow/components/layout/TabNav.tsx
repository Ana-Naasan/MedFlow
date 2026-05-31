"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

interface TabNavProps {
  patientId: string
}

interface TabItem {
  label: string
  href: string
}

function buildTabs(patientId: string): readonly TabItem[] {
  return [
    { label: "Profile", href: `/patients/${patientId}/profile` },
    { label: "Encounters/Appts", href: `/patients/${patientId}/encounters` },
    { label: "eDocuments", href: `/patients/${patientId}/edocuments` },
    { label: "Files", href: `/patients/${patientId}/files` },
    { label: "Investigations", href: `/patients/${patientId}/investigations` },
    { label: "Notes", href: `/patients/${patientId}/notes` },
    { label: "Billing", href: `/patients/${patientId}/billing` },
  ] as const
}

export function TabNav({ patientId }: TabNavProps) {
  const pathname = usePathname()
  const tabs = buildTabs(patientId)

  return (
    <nav
      className="shrink-0 border-b-2"
      style={{
        borderColor: "var(--mf-ink)",
        background: "var(--mf-paper)",
      }}
      aria-label="Patient record sections"
    >
      <ul
        className="flex items-end gap-0 overflow-x-auto px-4 sm:px-6 scrollbar-none"
        role="tablist"
        aria-orientation="horizontal"
      >
        {tabs.map(({ label, href }) => {
          const isActive = pathname === href || pathname.startsWith(`${href}/`)

          return (
            <li key={href} role="presentation">
              <Link
                href={href}
                role="tab"
                aria-selected={isActive}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "inline-flex h-10 min-h-[44px] items-center whitespace-nowrap px-4 text-sm font-semibold transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]",
                  isActive
                    ? "border-b-2 text-[var(--mf-ink)]"
                    : "border-b-2 border-transparent text-[var(--mf-ink-soft)] hover:text-[var(--mf-ink)]"
                )}
                style={
                  isActive
                    ? { borderBottomColor: "var(--mf-accent)" }
                    : undefined
                }
              >
                {label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
