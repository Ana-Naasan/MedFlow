"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "../../lib/utils";

const TABS = [
  { label: "Profile", slug: "profile" },
  { label: "Packet", slug: "packet" },
  { label: "Records", slug: "records" },
  { label: "eDocuments", slug: "edocuments" },
  { label: "Investigations", slug: "investigations" },
  { label: "Notes", slug: "notes" },
  { label: "Billing", slug: "billing" },
] as const;

export function PatientTabs({ patientId }: { patientId: string }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Patient record sections"
      className="flex items-center gap-1 overflow-x-auto border-b border-border px-6"
      data-testid="patient-tabs"
    >
      {TABS.map((tab) => {
        const href = `/patients/${patientId}/${tab.slug}`;
        const active = pathname === href || pathname.startsWith(href + "/");
        return (
          <Link
            key={tab.slug}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "whitespace-nowrap rounded-t-md px-4 py-3 text-sm transition-all duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
              active
                ? "border-b-2 border-accent font-semibold text-foreground"
                : "border-b-2 border-transparent font-medium text-mf-ink-soft hover:bg-bg-subtle hover:text-foreground",
            )}
            data-testid={`tab-${tab.slug}`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
