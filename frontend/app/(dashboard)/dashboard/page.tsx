import Link from "next/link"
import { CalendarDays, FlaskConical, CheckSquare, ChevronRight } from "lucide-react"
import { patients } from "@/lib/mock-data/patients"
import { DashboardPageClient } from "@/components/dashboard/DashboardPageClient"

const STATS = [
  {
    label: "Patients Today",
    value: 8,
    icon: CalendarDays,
    iconClass: "text-[var(--mf-accent)]",
    iconWrapClass: "bg-[var(--mf-accent-soft)]",
  },
  {
    label: "Pending Labs",
    value: 3,
    icon: FlaskConical,
    iconClass: "text-warning",
    iconWrapClass: "bg-[var(--mf-warm-tint)]",
  },
  {
    label: "Tasks",
    value: 5,
    icon: CheckSquare,
    iconClass: "text-success",
    iconWrapClass: "bg-[var(--mf-accent-soft)]",
  },
] as const

export default function DashboardPage() {
  const today = new Date().toLocaleDateString("en-CA", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="space-y-1">
        <p className="mf-eyebrow mb-1">Clinical dashboard</p>
        <h1 className="mf-display text-[32px] font-semibold leading-tight">
          Good morning, Dr. Bella Wu
        </h1>
        <p className="text-sm" style={{ color: "var(--mf-ink-soft)" }}>
          {today}
        </p>
      </div>

      <section aria-label="Summary statistics">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {STATS.map(({ label, value, icon: Icon, iconClass, iconWrapClass }) => (
            <div key={label} className="mf-surface-card p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium" style={{ color: "var(--mf-ink-soft)" }}>
                  {label}
                </p>
                <div
                  className={`flex size-9 items-center justify-center rounded-lg ${iconWrapClass}`}
                  aria-hidden="true"
                >
                  <Icon className={`size-4 ${iconClass}`} />
                </div>
              </div>
              <p className="mt-3 text-3xl font-semibold tabular-nums text-foreground">
                {value}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section aria-label="Recently accessed patients">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="mf-display text-lg font-semibold">Recently Accessed</h2>
          <Link
            href="/directory"
            className="flex items-center gap-1 text-xs font-semibold hover:underline"
            style={{ color: "var(--mf-accent)" }}
          >
            All patients <ChevronRight className="size-3" aria-hidden="true" />
          </Link>
        </div>
        <DashboardPageClient allPatients={patients} />
      </section>
    </div>
  )
}
