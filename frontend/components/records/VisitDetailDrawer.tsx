"use client"

import { useState } from "react"
import { Pill, FileText, ChevronDown, ChevronUp } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import type { Encounter, FileRecord, EncounterType } from "@/lib/types"

// ─── Type config ──────────────────────────────────────────────────────────────

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

// ─── Vitals grid ──────────────────────────────────────────────────────────────

interface VitalsGridProps {
  vitals: NonNullable<Encounter["vitals"]>
}

function VitalsGrid({ vitals }: VitalsGridProps) {
  type VitalEntry = { label: string; value: string }
  const items: VitalEntry[] = []
  if (vitals.bp) items.push({ label: "BP", value: vitals.bp })
  if (vitals.hr) items.push({ label: "HR", value: `${vitals.hr} bpm` })
  if (vitals.temp) items.push({ label: "Temp", value: `${vitals.temp}°C` })
  if (vitals.o2sat) items.push({ label: "SpO₂", value: `${vitals.o2sat}%` })
  if (vitals.weight) items.push({ label: "Weight", value: `${vitals.weight} kg` })
  if (vitals.height) items.push({ label: "Height", value: `${vitals.height} cm` })

  if (items.length === 0) return null

  return (
    <section>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        Vitals
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {items.map((item) => (
          <div
            key={item.label}
            className="bg-bg-subtle rounded-lg p-3 text-center"
          >
            <p className="text-xs text-muted-foreground mb-0.5">{item.label}</p>
            <p className="text-sm font-medium text-foreground">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

// ─── Collapsible SOAP section ─────────────────────────────────────────────────

interface SoapSectionProps {
  title: string
  content: string
  defaultOpen?: boolean
}

function SoapSection({ title, content, defaultOpen = false }: SoapSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center justify-between w-full px-3 py-2.5 text-left hover:bg-bg-subtle transition-colors"
        aria-expanded={open}
      >
        <span className="text-xs font-semibold text-foreground">{title}</span>
        {open ? (
          <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 border-t border-border">
          <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
            {content}
          </p>
        </div>
      )}
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────

interface VisitDetailDrawerProps {
  encounter: Encounter | null
  attachedFiles: FileRecord[]
  open: boolean
  onOpenChange: (open: boolean) => void
  onFileClick: (file: FileRecord) => void
}

export function VisitDetailDrawer({
  encounter,
  attachedFiles,
  open,
  onOpenChange,
  onFileClick,
}: VisitDetailDrawerProps) {
  if (!encounter) return null

  const typeColor = ENCOUNTER_TYPE_COLORS[encounter.type]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[480px] sm:w-[480px] overflow-y-auto flex flex-col gap-0 p-0"
      >
        {/* Header */}
        <SheetHeader className="px-5 pt-5 pb-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${typeColor.bg} ${typeColor.text}`}
            >
              {typeColor.label}
            </span>
            <span className="font-mono text-xs text-muted-foreground">
              {encounter.date}
            </span>
          </div>
          <SheetTitle className="text-sm font-medium text-foreground">
            {encounter.chiefComplaint}
          </SheetTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {encounter.physician}
          </p>
        </SheetHeader>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Summary */}
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Summary
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              {encounter.summary}
            </p>
          </section>

          {/* Vitals */}
          {encounter.vitals && (
            <>
              <Separator />
              <VitalsGrid vitals={encounter.vitals} />
            </>
          )}

          {/* SOAP Notes */}
          {encounter.soapNotes && (
            <>
              <Separator />
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  SOAP Notes
                </h3>
                <div className="space-y-2">
                  <SoapSection
                    title="Subjective"
                    content={encounter.soapNotes.subjective}
                    defaultOpen
                  />
                  <SoapSection
                    title="Objective"
                    content={encounter.soapNotes.objective}
                  />
                  <SoapSection
                    title="Assessment"
                    content={encounter.soapNotes.assessment}
                  />
                  <SoapSection
                    title="Plan"
                    content={encounter.soapNotes.plan}
                  />
                </div>
              </section>
            </>
          )}

          {/* Prescriptions */}
          {encounter.prescriptions && encounter.prescriptions.length > 0 && (
            <>
              <Separator />
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Prescriptions
                </h3>
                <ul className="space-y-1.5">
                  {encounter.prescriptions.map((rx) => (
                    <li key={rx} className="flex items-start gap-2">
                      <Pill className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
                      <span className="text-sm text-foreground leading-snug">
                        {rx}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}

          {/* Attached documents */}
          {attachedFiles.length > 0 && (
            <>
              <Separator />
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Attached Documents ({attachedFiles.length})
                </h3>
                <div className="space-y-1">
                  {attachedFiles.map((file) => (
                    <button
                      key={file.id}
                      type="button"
                      onClick={() => onFileClick(file)}
                      className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg hover:bg-bg-subtle transition-colors group border border-border"
                    >
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-foreground group-hover:text-primary truncate flex-1">
                        {file.name}
                      </span>
                      <span className="text-xs text-muted-foreground font-mono shrink-0">
                        {file.uploadedAt.split("T")[0]}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
