"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { signOut } from "next-auth/react"
import {
  FileText,
  CalendarDays,
  Users,
  FileEdit,
  CheckSquare,
  Settings,
  LogOut,
  Search,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { useMedFlowStore } from "@/lib/store"
import { BrandLogo } from "@/components/brand/BrandLogo"

interface NavItem {
  label: string
  href: string
  icon: React.ElementType
}

const NAV_ITEMS: readonly NavItem[] = [
  { label: "Records", href: "/dashboard", icon: FileText },
  { label: "AI Review", href: "/ai-review", icon: Sparkles },
  { label: "Scheduler", href: "/scheduler", icon: CalendarDays },
  { label: "Directory", href: "/directory", icon: Users },
  { label: "Memos", href: "/memos", icon: FileEdit },
  { label: "Tasks", href: "/tasks", icon: CheckSquare },
  { label: "Utilities", href: "/utilities", icon: Settings },
] as const

export function Sidebar() {
  const pathname = usePathname()
  const setSearchOpen = useMedFlowStore((s) => s.setSearchOpen)

  function handleSignOut() {
    void signOut({ callbackUrl: "/" })
  }

  return (
    <aside
      className="flex h-screen w-16 flex-col border-r-2 lg:w-60"
      style={{
        background: "var(--mf-paper)",
        borderColor: "var(--mf-ink)",
      }}
      aria-label="Main navigation"
    >
      <div
        className="flex h-14 shrink-0 items-center justify-center border-b-2 px-2 lg:justify-start lg:px-4"
        style={{ borderColor: "var(--mf-ink)" }}
      >
        <BrandLogo
          href="/dashboard"
          size="sm"
          wordmarkClassName="hidden lg:inline"
          className="min-h-0 lg:min-h-[44px]"
        />
      </div>

      <div className="hidden px-3 pt-3 lg:block">
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="flex min-h-[44px] w-full items-center gap-2 rounded-lg border-2 px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
          style={{
            borderColor: "var(--mf-ink)",
            background: "var(--mf-paper)",
            color: "var(--mf-ink-soft)",
          }}
          aria-label="Search patients"
        >
          <Search className="size-4 shrink-0" aria-hidden="true" />
          <span className="flex-1 text-left">Search patients...</span>
          <kbd
            className="shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] leading-none"
            style={{
              borderColor: "var(--mf-paper-2)",
              background: "var(--mf-paper-2)",
              color: "var(--mf-ink-soft)",
            }}
          >
            K
          </kbd>
        </button>
      </div>

      <div className="flex justify-center px-2 pt-3 lg:hidden">
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="mf-icon-btn"
          aria-label="Search patients"
        >
          <Search className="size-4" aria-hidden="true" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Sidebar navigation">
        <ul className="space-y-1" role="list">
          {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
            const isActive =
              href === "/dashboard"
                ? pathname === "/dashboard" || pathname.startsWith("/patients")
                : pathname.startsWith(href)

            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  title={label}
                  className={cn(
                    "group flex min-h-[44px] items-center justify-center gap-3 rounded-lg border-l-2 px-2 py-2.5 text-sm font-semibold transition-colors duration-150 lg:justify-start lg:px-3",
                    isActive
                      ? "border-[var(--mf-clinician-line)]"
                      : "border-transparent"
                  )}
                  style={{
                    background: isActive ? "var(--mf-clinician)" : "transparent",
                    color: isActive ? "var(--mf-ink)" : "var(--mf-ink-soft)",
                  }}
                >
                  <Icon
                    className="size-[18px] shrink-0"
                    style={{
                      color: isActive ? "var(--mf-accent)" : "var(--mf-ink-soft)",
                    }}
                    aria-hidden="true"
                  />
                  <span className="hidden lg:block">{label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="shrink-0">
        <Separator className="bg-[var(--mf-ink)]/15" />
        <div className="flex flex-col items-center gap-2 p-2 lg:flex-row lg:items-center lg:gap-3 lg:p-3">
          <Avatar
            className="hidden shrink-0 border-2 lg:flex"
            style={{ borderColor: "var(--mf-clinician-line)" }}
          >
            <AvatarFallback
              className="text-xs font-semibold"
              style={{
                background: "var(--mf-clinician)",
                color: "var(--mf-accent)",
              }}
            >
              BW
            </AvatarFallback>
          </Avatar>
          <div className="hidden min-w-0 flex-1 lg:block">
            <p className="mf-display truncate text-sm font-semibold leading-tight">
              Dr. Bella Wu
            </p>
            <p className="truncate text-xs leading-tight" style={{ color: "var(--mf-ink-soft)" }}>
              Family Physician
            </p>
          </div>
          <button
            type="button"
            onClick={handleSignOut}
            aria-label="Sign out"
            className="mf-icon-btn lg:ml-auto"
          >
            <LogOut className="size-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  )
}
