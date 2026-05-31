"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CalendarDays,
  CheckSquare,
  FileEdit,
  FileText,
  LogOut,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

import { cn } from "../../lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

const NAV_ITEMS: readonly NavItem[] = [
  { label: "Records", href: "/dashboard", icon: FileText },
  { label: "Directory", href: "/directory", icon: Users },
  { label: "Scheduler", href: "/scheduler", icon: CalendarDays },
  { label: "Memos", href: "/memos", icon: FileEdit },
  { label: "Tasks", href: "/tasks", icon: CheckSquare },
  { label: "Utilities", href: "/utilities", icon: Settings },
] as const;

/**
 * Clinician sidebar. Ported from medflow but shorn of the global search modal
 * + NextAuth signOut (not in scope for Phase 1 — we don't have a real session
 * to end). The "Sign out" button just routes back to the role-select home.
 *
 * The active-link detection mirrors medflow: exact match OR child-route match
 * (so `/dashboard/anything` highlights "Records" too).
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex h-screen w-16 flex-col border-r-2 border-mf-ink bg-mf-paper lg:w-60"
      aria-label="Main navigation"
    >
      <div className="flex h-14 shrink-0 items-center justify-center border-b-2 border-mf-ink px-2 lg:justify-start lg:px-4">
        <Link
          href="/dashboard"
          className="mf-display text-lg font-semibold text-mf-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent"
          aria-label="Umraa home"
        >
          <span className="lg:hidden">U</span>
          <span className="hidden lg:inline">Umraa</span>
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 lg:p-3">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-[44px] items-center gap-3 rounded-lg border-l-4 px-3 py-2 text-sm transition-colors",
                    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent",
                    active
                      ? "border-mf-clinician-line bg-mf-clinician text-mf-ink font-semibold"
                      : "border-transparent text-mf-ink-soft hover:bg-mf-paper-2 hover:text-mf-ink",
                  )}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                >
                  <Icon className="size-4 shrink-0" aria-hidden />
                  <span className="hidden lg:inline">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t-2 border-mf-ink p-2 lg:p-3">
        <Link
          href="/"
          className="flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2 text-sm text-mf-ink-soft transition-colors hover:bg-mf-paper-2 hover:text-mf-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mf-accent"
          data-testid="sign-out"
        >
          <LogOut className="size-4 shrink-0" aria-hidden />
          <span className="hidden lg:inline">Switch role</span>
        </Link>
      </div>
    </aside>
  );
}
