"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { signOut } from "next-auth/react"
import { BrandLogo } from "@/components/brand/BrandLogo"

const NAV = [
  { href: "/patient/dashboard", label: "Home" },
  { href: "/patient/care-plan", label: "Care plan" },
] as const

export function PatientTopNav() {
  const pathname = usePathname()

  return (
    <header
      className="sticky top-0 z-50 border-b-2"
      style={{
        background: "var(--mf-paper)",
        borderColor: "var(--mf-ink)",
      }}
    >
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between gap-3 px-4 sm:gap-4 sm:px-6">
        <BrandLogo href="/patient/dashboard" size="sm" className="min-h-0 shrink-0" />
        <nav
          className="hidden items-center gap-1 sm:flex"
          aria-label="Patient navigation"
        >
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="inline-flex min-h-[44px] items-center rounded-lg px-3 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
              style={{
                background:
                  pathname === href ? "var(--mf-accent-soft)" : "transparent",
                color:
                  pathname === href ? "var(--mf-accent)" : "var(--mf-ink-soft)",
              }}
              aria-current={pathname === href ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
        <button
          type="button"
          onClick={() => void signOut({ callbackUrl: "/" })}
          className="mf-btn-secondary shrink-0 px-3 py-2 text-sm"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
