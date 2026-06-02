"use client"

import Link from "next/link"
import {
  Settings2,
  Plug,
  Workflow,
  FileType,
  Users,
  ExternalLink,
  RotateCcw,
  type LucideIcon,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useClinicToolsStore } from "@/lib/clinic-tools-store"
import {
  UTILITY_TOGGLES,
  UTILITY_LINKS,
  BILLING_CODE_REFERENCE,
  CLINIC_STAFF,
  type UtilityCategory,
} from "@/lib/mock-data/utilities"
import { HealthCard } from "@/components/clinic/HealthCard"
import { ConnectorsList } from "@/components/clinic/ConnectorsList"
import { AuditLogTable } from "@/components/clinic/AuditLogTable"

const CATEGORY_META: Record<UtilityCategory, { title: string; icon: LucideIcon }> = {
  integrations: { title: "Integrations", icon: Plug },
  workflow: { title: "Workflow", icon: Workflow },
  templates: { title: "Templates", icon: FileType },
  account: { title: "Account", icon: Users },
}

export function UtilitiesPageClient() {
  const utilityEnabled = useClinicToolsStore((s) => s.utilityEnabled)
  const setUtilityEnabled = useClinicToolsStore((s) => s.setUtilityEnabled)
  const resetClinicTools = useClinicToolsStore((s) => s.resetClinicTools)

  const categories: UtilityCategory[] = ["integrations", "workflow", "templates"]

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mf-eyebrow mb-1">Clinician</p>
          <h1 className="mf-display text-2xl font-semibold leading-tight">Utilities</h1>
          <p className="mt-1 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
            Clinic settings, integrations, and quick tools
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            if (confirm("Reset memos, tasks, and utility toggles to defaults?")) {
              resetClinicTools()
            }
          }}
          className="mf-btn-secondary text-sm"
        >
          <RotateCcw className="size-4" aria-hidden />
          Reset demo data
        </button>
      </div>

      <HealthCard />
      <ConnectorsList />
      <AuditLogTable />

      {categories.map((category) => {
        const meta = CATEGORY_META[category]
        const Icon = meta.icon
        const toggles = UTILITY_TOGGLES.filter((t) => t.category === category)

        return (
          <section key={category} aria-labelledby={`util-${category}`}>
            <h2
              id={`util-${category}`}
              className="mb-3 flex items-center gap-2 text-lg font-semibold"
            >
              <Icon className="size-5 text-[var(--mf-accent)]" aria-hidden />
              {meta.title}
            </h2>
            <ul className="space-y-2">
              {toggles.map((toggle) => {
                const enabled = utilityEnabled[toggle.id] ?? toggle.enabled
                return (
                  <li key={toggle.id} className="mf-surface-card flex items-center gap-4 p-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold">{toggle.label}</p>
                      <p className="mt-0.5 text-sm" style={{ color: "var(--mf-ink-soft)" }}>
                        {toggle.description}
                      </p>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enabled}
                      aria-label={`${toggle.label} ${enabled ? "on" : "off"}`}
                      onClick={() => setUtilityEnabled(toggle.id, !enabled)}
                      className={cn(
                        "relative h-7 w-12 shrink-0 rounded-full border-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]",
                        enabled
                          ? "border-[var(--mf-accent)] bg-[var(--mf-accent)]"
                          : "border-[var(--mf-ink)] bg-[var(--mf-paper-2)]"
                      )}
                    >
                      <span
                        className={cn(
                          "absolute top-0.5 size-5 rounded-full bg-white shadow transition-[left]",
                          enabled ? "left-[22px]" : "left-0.5"
                        )}
                      />
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}

      <section aria-labelledby="util-quick-links">
        <h2 id="util-quick-links" className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <Settings2 className="size-5 text-[var(--mf-accent)]" aria-hidden />
          Quick links
        </h2>
        <ul className="grid gap-2 sm:grid-cols-3">
          {UTILITY_LINKS.map((link) => (
            <li key={link.id}>
              <Link
                href={link.href}
                className="mf-surface-card flex h-full flex-col p-4 transition-shadow hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--mf-accent)]"
              >
                <span className="flex items-center gap-1.5 text-sm font-semibold">
                  {link.label}
                  <ExternalLink className="size-3.5 opacity-60" aria-hidden />
                </span>
                <span className="mt-1 text-xs leading-snug" style={{ color: "var(--mf-ink-soft)" }}>
                  {link.description}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section id="billing-codes" aria-labelledby="util-billing">
        <h2 id="util-billing" className="mb-3 text-lg font-semibold">
          Alberta billing codes (reference)
        </h2>
        <div className="mf-surface-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr
                className="border-b-2"
                style={{ borderColor: "var(--mf-ink)", background: "var(--mf-paper-2)" }}
              >
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Code</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Description</th>
                <th className="mf-eyebrow px-4 py-3 text-right !text-[10px]">Amount</th>
              </tr>
            </thead>
            <tbody>
              {BILLING_CODE_REFERENCE.map((row) => (
                <tr
                  key={row.code}
                  className="border-b last:border-0"
                  style={{ borderColor: "var(--mf-paper-2)" }}
                >
                  <td className="px-4 py-3 font-mono font-semibold">{row.code}</td>
                  <td className="px-4 py-3" style={{ color: "var(--mf-ink-soft)" }}>
                    {row.description}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium">
                    ${row.amount.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="util-staff">
        <h2 id="util-staff" className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <Users className="size-5 text-[var(--mf-accent)]" aria-hidden />
          Clinic staff
        </h2>
        <div className="mf-surface-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr
                className="border-b-2"
                style={{ borderColor: "var(--mf-ink)", background: "var(--mf-paper-2)" }}
              >
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Name</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Role</th>
                <th className="mf-eyebrow px-4 py-3 text-left !text-[10px]">Email</th>
              </tr>
            </thead>
            <tbody>
              {CLINIC_STAFF.map((person) => (
                <tr
                  key={person.email}
                  className="border-b last:border-0"
                  style={{ borderColor: "var(--mf-paper-2)" }}
                >
                  <td className="px-4 py-3 font-medium">{person.name}</td>
                  <td className="px-4 py-3" style={{ color: "var(--mf-ink-soft)" }}>
                    {person.role}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{person.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
