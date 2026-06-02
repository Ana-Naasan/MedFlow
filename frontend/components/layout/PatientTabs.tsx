"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const TABS = [
  { label: "AI Review",      slug: "packet" },
  { label: "Profile",        slug: "profile" },
  { label: "Records",        slug: "records" },
  { label: "eDocuments",     slug: "edocuments" },
  { label: "Investigations", slug: "investigations" },
  { label: "Notes",          slug: "notes" },
  { label: "Billing",        slug: "billing" },
] as const

export function PatientTabs({ patientId }: { patientId: string }) {
  const pathname = usePathname()

  return (
    <nav
      aria-label="Patient record sections"
      className="flex items-center gap-1 border-b border-[var(--border)] px-6 overflow-x-auto scrollbar-none"
    >
      {TABS.map((tab) => {
        const href = `/patients/${patientId}/${tab.slug}`
        const isActive = pathname === href || pathname.startsWith(href + "/")

        return (
          <Link
            key={tab.slug}
            href={href}
            aria-current={isActive ? "page" : undefined}
            className={[
              "px-4 py-3 text-sm transition-all duration-150 whitespace-nowrap rounded-t-md",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2",
              isActive
                ? "font-semibold text-[var(--foreground)] border-b-2 border-[var(--accent)]"
                : "font-medium text-[var(--text-secondary)] border-b-2 border-transparent hover:text-[var(--foreground)] hover:bg-[var(--bg-subtle)]",
            ].join(" ")}
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
