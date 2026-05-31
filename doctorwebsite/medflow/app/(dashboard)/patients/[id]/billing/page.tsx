"use client"

import { useMemo, useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { ExternalLink, Download } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { getBillingByPatientId } from "@/lib/mock-data/billing"
import type { BillingEntry, BillingStatus } from "@/lib/types"

// ─── Animation ───────────────────────────────────────────────────────────────

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] },
  },
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const currency = new Intl.NumberFormat("en-CA", {
  style: "currency",
  currency: "CAD",
})

function generateMonthlyData(
  entries: BillingEntry[],
): Array<{ month: string; amount: number }> {
  const result: Array<{ month: string; amount: number }> = []
  for (let i = 11; i >= 0; i--) {
    const d = new Date()
    d.setMonth(d.getMonth() - i)
    const monthStr = d.toLocaleString("default", { month: "short" })
    const year = d.getFullYear()
    const month = d.getMonth()
    const total = entries
      .filter((e) => {
        const ed = new Date(e.date)
        return ed.getFullYear() === year && ed.getMonth() === month
      })
      .reduce((sum, e) => sum + e.amount, 0)
    result.push({ month: monthStr, amount: Number(total.toFixed(2)) })
  }
  return result
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  BillingStatus,
  { dot: string; text: string; bg: string; label: string }
> = {
  paid: { dot: "bg-success", text: "text-success", bg: "bg-success/10", label: "Paid" },
  pending: { dot: "bg-warning", text: "text-warning", bg: "bg-warning/10", label: "Pending" },
  rejected: { dot: "bg-danger", text: "text-danger", bg: "bg-danger/10", label: "Rejected" },
}

function BillingStatusBadge({ status }: { status: BillingStatus }) {
  const c = STATUS_CONFIG[status]
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  subtitle,
}: {
  label: string
  value: string
  subtitle?: string
}) {
  return (
    <div className="bg-bg-surface border border-border rounded-xl p-5">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">
        {label}
      </p>
      <p className="text-2xl font-semibold font-mono text-foreground">{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
    </div>
  )
}

// ─── Detail drawer ────────────────────────────────────────────────────────────

interface BillingDetailDrawerProps {
  entry: BillingEntry | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function BillingDetailDrawer({ entry, open, onOpenChange }: BillingDetailDrawerProps) {
  if (!entry) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[400px] sm:w-[400px] overflow-y-auto p-0">
        <SheetHeader className="px-5 pt-5 pb-4 border-b border-border">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-primary bg-primary/10 px-1.5 py-0.5 rounded">
              {entry.serviceCode}
            </span>
            <BillingStatusBadge status={entry.status} />
          </div>
          <SheetTitle className="text-sm font-medium text-foreground">
            {entry.description}
          </SheetTitle>
        </SheetHeader>

        <div className="px-5 py-5 space-y-5">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">Date</p>
              <p className="font-medium text-foreground font-mono">{entry.date}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">Amount</p>
              <p className="font-medium text-foreground font-mono text-base">
                {currency.format(entry.amount)}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">Service Code</p>
              <p className="font-medium text-foreground font-mono">{entry.serviceCode}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">Status</p>
              <BillingStatusBadge status={entry.status} />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
              Description
            </p>
            <p className="text-sm text-text-secondary leading-relaxed">{entry.description}</p>
          </div>

          <div className="flex flex-col gap-2 pt-2 border-t border-border">
            <Button variant="ghost" size="sm" className="justify-start gap-2">
              <ExternalLink className="w-3.5 h-3.5" />
              View Originating Visit
            </Button>
            <Button variant="ghost" size="sm" className="justify-start gap-2">
              <Download className="w-3.5 h-3.5" />
              Download Claim
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { id } = useParams<{ id: string }>()
  const billingEntries = getBillingByPatientId(id)

  const [selectedEntry, setSelectedEntry] = useState<BillingEntry | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const monthlyData = useMemo(() => generateMonthlyData(billingEntries), [billingEntries])

  const stats = useMemo(() => {
    const currentYear = new Date().getFullYear()
    const totalYtd = billingEntries
      .filter((e) => new Date(e.date).getFullYear() === currentYear)
      .reduce((sum, e) => sum + e.amount, 0)
    const outstanding = billingEntries
      .filter((e) => e.status === "pending")
      .reduce((sum, e) => sum + e.amount, 0)
    const paidEntries = billingEntries
      .filter((e) => e.status === "paid")
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    const lastPayment = paidEntries[0]?.date ?? null
    return { totalYtd, outstanding, lastPayment }
  }, [billingEntries])

  const sortedEntries = useMemo(
    () =>
      [...billingEntries].sort(
        (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
      ),
    [billingEntries],
  )

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatCard
          label="Total Billed YTD"
          value={currency.format(stats.totalYtd)}
          subtitle={`${new Date().getFullYear()} to date`}
        />
        <StatCard
          label="Outstanding Balance"
          value={currency.format(stats.outstanding)}
          subtitle="Pending claims"
        />
        <StatCard
          label="Last Payment"
          value={stats.lastPayment ?? "—"}
          subtitle={stats.lastPayment ? "Most recent paid claim" : "No payments yet"}
        />
      </div>

      {/* Chart */}
      <div className="bg-bg-surface border border-border rounded-xl p-5 mb-6">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-4">
          Billing — Last 12 Months
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={monthlyData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v}`}
            />
            <Tooltip
              cursor={{ fill: "var(--bg-subtle)" }}
              contentStyle={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(value) => [currency.format(Number(value)), "Billed"] as [string, string]}
            />
            <Bar dataKey="amount" fill="var(--primary)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Table */}
      <div className="bg-bg-surface border border-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Date", "Service Code", "Description", "Amount", "Status", ""].map((col, i) => (
                <th
                  key={col || `col-${i}`}
                  className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedEntries.map((entry) => (
              <tr
                key={entry.id}
                className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer group relative"
                onClick={() => {
                  setSelectedEntry(entry)
                  setDrawerOpen(true)
                }}
              >
                <td className="relative px-4 py-3 font-mono text-xs text-muted-foreground">
                  <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                  {entry.date}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-foreground">{entry.serviceCode}</td>
                <td className="px-4 py-3 text-foreground max-w-[220px] truncate">
                  {entry.description}
                </td>
                <td className="px-4 py-3 font-mono text-foreground font-medium">
                  {currency.format(entry.amount)}
                </td>
                <td className="px-4 py-3">
                  <BillingStatusBadge status={entry.status} />
                </td>
                <td className="px-4 py-3">
                  <Button variant="ghost" size="sm" className="h-6 text-xs px-2">
                    View
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {sortedEntries.length === 0 && (
          <div className="py-16 text-center">
            <p className="text-sm text-muted-foreground">No billing records found</p>
          </div>
        )}
      </div>

      <BillingDetailDrawer
        entry={selectedEntry}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </motion.div>
  )
}
