"use client"

import { useMemo, useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import { FileText, Search } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { VisitDetailDrawer } from "@/components/records/VisitDetailDrawer"
import { FilePreviewModal } from "@/components/records/FilePreviewModal"

import { getEncountersByPatientId } from "@/lib/mock-data/encounters"
import { getFilesByPatientId } from "@/lib/mock-data/files"
import type { Encounter, EncounterType, FileRecord } from "@/lib/types"

// ─── Animation ───────────────────────────────────────────────────────────────

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.25, 0.1, 0.25, 1] },
  },
}

const containerVariants: Variants = {
  animate: { transition: { staggerChildren: 0.05 } },
}

const cardVariants: Variants = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
}

// ─── Encounter type config ────────────────────────────────────────────────────

const ENCOUNTER_TYPE_COLORS: Record<
  EncounterType,
  { bg: string; text: string; label: string }
> = {
  "office-visit": { bg: "bg-primary/10", text: "text-primary", label: "Office Visit" },
  telehealth: { bg: "bg-purple-100", text: "text-purple-700", label: "Telehealth" },
  "walk-in": { bg: "bg-success/10", text: "text-success", label: "Walk-in" },
  emergency: { bg: "bg-danger/10", text: "text-danger", label: "Emergency" },
  specialist: { bg: "bg-warning/10", text: "text-warning", label: "Specialist" },
}

// ─── VisitCard ────────────────────────────────────────────────────────────────

interface VisitCardProps {
  encounter: Encounter
  files: FileRecord[]
  onOpen: () => void
  onFileClick: (file: FileRecord) => void
}

function VisitCard({ encounter, files, onOpen, onFileClick }: VisitCardProps) {
  const typeColor = ENCOUNTER_TYPE_COLORS[encounter.type]
  const v = encounter.vitals

  return (
    <motion.div variants={cardVariants} className="relative pl-6">
      {/* timeline dot */}
      <div className="absolute left-0 top-5 w-3.5 h-3.5 rounded-full bg-bg-surface border-2 border-primary" />

      <div className="bg-bg-surface border border-border rounded-xl p-5 hover:shadow-[var(--shadow-sm)] transition-shadow">
        {/* Header */}
        <div className="flex items-start justify-between mb-3 gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-muted-foreground">{encounter.date}</span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${typeColor.bg} ${typeColor.text}`}
              >
                {typeColor.label}
              </span>
            </div>
            <p className="text-sm font-medium text-foreground">{encounter.physician}</p>
          </div>
        </div>

        {/* Chief complaint */}
        <div className="mb-2">
          <span className="text-xs font-medium text-muted-foreground">Chief Complaint: </span>
          <span className="text-sm text-foreground">{encounter.chiefComplaint}</span>
        </div>

        {/* Summary */}
        <p className="text-sm text-text-secondary mb-3 line-clamp-2">{encounter.summary}</p>

        {/* Vitals */}
        {v && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 py-2 px-3 bg-bg-subtle rounded-lg text-xs">
            {v.bp && <span><span className="text-muted-foreground">BP </span>{v.bp}</span>}
            {v.hr && <span><span className="text-muted-foreground">HR </span>{v.hr}</span>}
            {v.temp && <span><span className="text-muted-foreground">Temp </span>{v.temp}°C</span>}
            {v.o2sat && <span><span className="text-muted-foreground">SpO₂ </span>{v.o2sat}%</span>}
            {v.weight && <span><span className="text-muted-foreground">Wt </span>{v.weight}kg</span>}
          </div>
        )}

        {/* Attached documents */}
        {files.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-medium text-muted-foreground mb-1.5">
              Attached Documents ({files.length})
            </p>
            <div className="space-y-1">
              {files.map((file) => (
                <button
                  key={file.id}
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onFileClick(file)
                  }}
                  className="flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-md hover:bg-bg-subtle transition-colors group"
                >
                  <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                  <span className="text-xs text-foreground group-hover:text-primary truncate">
                    {file.name}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground font-mono shrink-0">
                    {file.uploadedAt.split("T")[0]}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onOpen}>
            Open Full Note
          </Button>
          {files.length > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs">
              Download All
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <rect x="8" y="12" width="48" height="44" rx="4" stroke="var(--border)" strokeWidth="2" />
        <line x1="8" y1="24" x2="56" y2="24" stroke="var(--border)" strokeWidth="2" />
        <rect x="20" y="6" width="8" height="12" rx="2" stroke="var(--border)" strokeWidth="2" />
        <rect x="36" y="6" width="8" height="12" rx="2" stroke="var(--border)" strokeWidth="2" />
        <circle cx="24" cy="36" r="3" fill="var(--border)" />
        <circle cx="32" cy="36" r="3" fill="var(--border)" />
        <circle cx="40" cy="36" r="3" fill="var(--border)" />
      </svg>
      <p className="text-sm font-medium text-foreground">No visit records yet</p>
      <p className="text-xs text-muted-foreground">Encounters will appear here once recorded</p>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RecordsPage() {
  const { id } = useParams<{ id: string }>()

  const [selectedEncounter, setSelectedEncounter] = useState<Encounter | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<FileRecord | null>(null)
  const [fileModalOpen, setFileModalOpen] = useState(false)
  const [filterType, setFilterType] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState("")

  const allEncounters = getEncountersByPatientId(id)
  const filesForPatient = getFilesByPatientId(id)

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return allEncounters
      .filter((e) => {
        const typeMatch = filterType === "all" || e.type === filterType
        const searchMatch =
          q === "" ||
          e.chiefComplaint.toLowerCase().includes(q) ||
          e.summary.toLowerCase().includes(q) ||
          e.physician.toLowerCase().includes(q)
        return typeMatch && searchMatch
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  }, [allEncounters, filterType, searchQuery])

  const drawerFiles = selectedEncounter
    ? filesForPatient.filter((f) => selectedEncounter.attachedDocuments?.includes(f.id))
    : []

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" className="space-y-5">
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search visits..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-9 text-sm"
            aria-label="Search visits"
          />
        </div>
        <Select value={filterType} onValueChange={(v) => setFilterType(v ?? "all")}>
          <SelectTrigger className="w-44" aria-label="Filter by visit type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="office-visit">Office Visit</SelectItem>
            <SelectItem value="telehealth">Telehealth</SelectItem>
            <SelectItem value="walk-in">Walk-in</SelectItem>
            <SelectItem value="emergency">Emergency</SelectItem>
            <SelectItem value="specialist">Specialist</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground ml-auto">
          {filtered.length} visit{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Timeline */}
      {filtered.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="relative">
          <div className="absolute left-[7px] top-3 bottom-3 w-px bg-border" />
          <motion.div
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="space-y-4"
          >
            {filtered.map((encounter) => (
              <VisitCard
                key={encounter.id}
                encounter={encounter}
                files={filesForPatient.filter((f) =>
                  encounter.attachedDocuments?.includes(f.id),
                )}
                onOpen={() => {
                  setSelectedEncounter(encounter)
                  setDrawerOpen(true)
                }}
                onFileClick={(file) => {
                  setSelectedFile(file)
                  setFileModalOpen(true)
                }}
              />
            ))}
          </motion.div>
        </div>
      )}

      {/* Visit detail drawer */}
      <VisitDetailDrawer
        encounter={selectedEncounter}
        attachedFiles={drawerFiles}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onFileClick={(file) => {
          setSelectedFile(file)
          setFileModalOpen(true)
        }}
      />

      {/* File preview modal */}
      <FilePreviewModal
        file={selectedFile}
        open={fileModalOpen}
        onOpenChange={setFileModalOpen}
      />
    </motion.div>
  )
}
