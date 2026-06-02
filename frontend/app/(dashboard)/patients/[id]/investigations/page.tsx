"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { getInvestigationsByPatientId } from "@/lib/mock-data/investigations"
import type { Investigation, InvestigationStatus, InvestigationType } from "@/lib/types"

// ─── Animation variants ───────────────────────────────────────────────────────

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] },
  },
}

const containerVariants: Variants = {
  animate: { transition: { staggerChildren: 0.04 } },
}

const itemVariants: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
}

// ─── StatusBadge ──────────────────────────────────────────────────────────────

interface StatusConfig {
  dot: string
  text: string
  bg: string
  label: string
}

const STATUS_CONFIG: Record<InvestigationStatus, StatusConfig> = {
  pending: {
    dot: "bg-warning",
    text: "text-warning",
    bg: "bg-warning/10",
    label: "Pending",
  },
  "in-progress": {
    dot: "bg-primary",
    text: "text-primary",
    bg: "bg-primary/10",
    label: "In Progress",
  },
  completed: {
    dot: "bg-success",
    text: "text-success",
    bg: "bg-success/10",
    label: "Completed",
  },
  cancelled: {
    dot: "bg-muted-foreground",
    text: "text-muted-foreground",
    bg: "bg-muted",
    label: "Cancelled",
  },
}

function StatusBadge({ status }: { status: InvestigationStatus }) {
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

// ─── EmptyState ───────────────────────────────────────────────────────────────

interface EmptyStateProps {
  onCreateNew: () => void
}

function EmptyState({ onCreateNew }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <rect x="12" y="14" width="32" height="38" rx="3" stroke="var(--border)" strokeWidth="2" />
        <rect x="22" y="10" width="12" height="8" rx="2" stroke="var(--border)" strokeWidth="2" />
        <line x1="20" y1="26" x2="36" y2="26" stroke="var(--border)" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="20" y1="32" x2="36" y2="32" stroke="var(--border)" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="20" y1="38" x2="30" y2="38" stroke="var(--border)" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="44" cy="44" r="8" stroke="var(--text-muted)" strokeWidth="2" />
        <line x1="49.5" y1="49.5" x2="55" y2="55" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <div>
        <p className="text-sm font-medium text-foreground">No investigations found</p>
        <p className="text-xs text-muted-foreground mt-1">Create one to get started</p>
      </div>
      <Button variant="default" size="sm" onClick={onCreateNew}>
        Create New
      </Button>
    </div>
  )
}

// ─── DetailDrawer ─────────────────────────────────────────────────────────────

interface DetailDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  investigation: Investigation | null
}

function DetailDrawer({ open, onOpenChange, investigation }: DetailDrawerProps) {
  const metaFields: Array<[string, string | undefined]> = [
    ["Date", investigation?.date],
    ["Type", investigation?.type],
    ["Source", investigation?.source],
    ["Ordered By", investigation?.orderedBy],
    ["Referring Physician", investigation?.referringPhysician ?? "—"],
  ]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[420px] sm:w-[420px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle className="text-base font-semibold pr-8">
            {investigation?.description}
          </SheetTitle>
          {investigation && <StatusBadge status={investigation.status} />}
        </SheetHeader>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-4 text-sm mb-6 px-4">
          {metaFields.map(([label, value]) => (
            <div key={label}>
              <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
              <p className="font-medium text-foreground capitalize">{value ?? "—"}</p>
            </div>
          ))}
        </div>

        {/* Status history */}
        <div className="mb-6 px-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Status History
          </p>
          <div className="space-y-2">
            {investigation?.statusHistory.map((h, i) => (
              <div key={i} className="flex items-center justify-between gap-2 text-sm">
                <StatusBadge status={h.status} />
                <span className="font-mono text-xs text-muted-foreground">{h.date}</span>
                <span className="text-xs text-muted-foreground truncate">{h.updatedBy}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Notes */}
        <div className="px-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Notes
          </p>
          <Textarea
            defaultValue={investigation?.notes ?? ""}
            placeholder="Add notes..."
            className="text-sm resize-none"
            rows={4}
            readOnly
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}

// ─── Tab config ───────────────────────────────────────────────────────────────

interface TabConfig {
  value: string
  label: string
  type: InvestigationType | null
}

const TAB_CONFIG: TabConfig[] = [
  { value: "all", label: "All", type: null },
  { value: "requisition", label: "Requisitions", type: "requisition" },
  { value: "referral", label: "Referrals", type: "referral" },
  { value: "or", label: "OR", type: "or" },
  { value: "misc", label: "Misc", type: "misc" },
]

// ─── InvestigationsTable ──────────────────────────────────────────────────────

interface InvestigationsTableProps {
  rows: Investigation[]
  onSelect: (inv: Investigation) => void
}

function InvestigationsTable({ rows, onSelect }: InvestigationsTableProps) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="bg-muted/40">
          <th className="pl-4 pr-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Date
          </th>
          <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Type
          </th>
          <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Description
          </th>
          <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Status
          </th>
          <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Ordered By
          </th>
          <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Actions
          </th>
        </tr>
      </thead>
      <motion.tbody variants={containerVariants} initial="initial" animate="animate">
        {rows.map((inv) => (
          <motion.tr
            variants={itemVariants}
            key={inv.id}
            className="border-b border-border relative cursor-pointer hover:bg-muted/30 transition-colors group"
            onClick={() => onSelect(inv)}
          >
            <td className="relative pl-4 pr-3 py-3 font-mono text-xs text-muted-foreground whitespace-nowrap">
              <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary opacity-0 group-hover:opacity-100 transition-opacity" />
              {inv.date}
            </td>
            <td className="px-3 py-3 capitalize text-foreground">{inv.type}</td>
            <td className="px-3 py-3 text-foreground max-w-[240px] truncate">
              {inv.description}
            </td>
            <td className="px-3 py-3">
              <StatusBadge status={inv.status} />
            </td>
            <td className="px-3 py-3 text-muted-foreground">{inv.orderedBy}</td>
            <td className="px-3 py-3">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs px-2"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect(inv)
                }}
              >
                View
              </Button>
            </td>
          </motion.tr>
        ))}
      </motion.tbody>
    </table>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InvestigationsPage() {
  const { id } = useParams<{ id: string }>()

  const [source, setSource] = useState<string>("all")
  const [activeTab, setActiveTab] = useState("all")
  const [selectedInvestigation, setSelectedInvestigation] = useState<Investigation | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const allInvestigations = getInvestigationsByPatientId(id)

  function getTabCount(tabValue: string): number {
    const tabType = TAB_CONFIG.find((t) => t.value === tabValue)?.type ?? null
    return allInvestigations.filter((inv) => {
      const sourceMatch = source === "all" || inv.source === source
      const typeMatch = tabType === null || inv.type === tabType
      return sourceMatch && typeMatch
    }).length
  }

  const filtered = allInvestigations.filter((inv) => {
    const sourceMatch = source === "all" || inv.source === source
    const activeType = TAB_CONFIG.find((t) => t.value === activeTab)?.type ?? null
    const tabMatch = activeType === null || inv.type === activeType
    return sourceMatch && tabMatch
  })

  function handleSelect(inv: Investigation): void {
    setSelectedInvestigation(inv)
    setDrawerOpen(true)
  }

  function handleCreateNew(): void {
    // placeholder — wire to create flow when implemented
  }

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" className="space-y-4">
      {/* Top controls */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Select value={source} onValueChange={(v) => setSource(v ?? "all")}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="Lab (LifeLabs)">Lab (LifeLabs)</SelectItem>
              <SelectItem value="Radiology">Radiology</SelectItem>
              <SelectItem value="Cardiology">Cardiology</SelectItem>
              <SelectItem value="Other">Other</SelectItem>
            </SelectContent>
          </Select>
          <a className="text-sm text-primary hover:underline cursor-pointer">details...</a>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="default" size="sm" onClick={handleCreateNew}>
            Create New
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              /* refresh */
            }}
          >
            Refresh All
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {TAB_CONFIG.map(({ value, label }) => {
            const count = getTabCount(value)
            return (
              <TabsTrigger key={value} value={value} className="gap-1.5">
                {label}
                <span className="inline-flex items-center justify-center rounded-full bg-muted px-1.5 py-0 text-xs font-medium text-muted-foreground min-w-[18px]">
                  {count}
                </span>
              </TabsTrigger>
            )
          })}
        </TabsList>

        {TAB_CONFIG.map(({ value }) => (
          <TabsContent key={value} value={value} className="mt-3">
            {filtered.length > 0 ? (
              <div className="rounded-lg border border-border overflow-hidden bg-bg-surface">
                <InvestigationsTable rows={filtered} onSelect={handleSelect} />
              </div>
            ) : (
              <EmptyState onCreateNew={handleCreateNew} />
            )}
          </TabsContent>
        ))}
      </Tabs>

      {/* Detail drawer */}
      <DetailDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        investigation={selectedInvestigation}
      />
    </motion.div>
  )
}
