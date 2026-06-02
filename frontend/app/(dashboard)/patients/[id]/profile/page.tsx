"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { motion, type Variants } from "framer-motion"
import {
  Pencil,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertTriangle,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { resolvePatient } from "@/lib/mock-data/patients"
import type { Patient, Allergy, Medication, Problem, EmergencyContact } from "@/lib/types"
import { cn } from "@/lib/utils"

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

function calculateAge(dob: string): number {
  return Math.floor(
    (Date.now() - new Date(dob).getTime()) / (1000 * 60 * 60 * 24 * 365.25),
  )
}

function formatDob(dob: string): string {
  return new Date(dob).toLocaleDateString("en-CA", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

// ─── Inline-edit field ───────────────────────────────────────────────────────

interface EditableFieldProps {
  label: string
  value: string
  fieldKey: keyof EditablePatientFields
  onSave: (key: keyof EditablePatientFields, value: string) => void
}

type EditablePatientFields = Pick<
  Patient,
  "phone" | "email" | "address"
>

function EditableField({ label, value, fieldKey, onSave }: EditableFieldProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [hovered, setHovered] = useState(false)

  function commit() {
    onSave(fieldKey, draft.trim())
    setEditing(false)
  }

  function cancel() {
    setDraft(value)
    setEditing(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") commit()
    if (e.key === "Escape") cancel()
  }

  return (
    <div
      className="flex items-start justify-between gap-2 py-2"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span className="text-xs text-muted-foreground w-28 shrink-0 pt-0.5">
        {label}
      </span>
      {editing ? (
        <Input
          className="h-7 text-sm flex-1"
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={handleKeyDown}
        />
      ) : (
        <span className="flex items-center gap-1 flex-1 text-sm text-foreground min-w-0">
          <span className="truncate">{value || <span className="text-muted-foreground italic">Not recorded</span>}</span>
          {hovered && (
            <button
              type="button"
              onClick={() => {
                setDraft(value)
                setEditing(true)
              }}
              className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              aria-label={`Edit ${label}`}
            >
              <Pencil size={12} />
            </button>
          )}
        </span>
      )}
    </div>
  )
}

// ─── Read-only field ─────────────────────────────────────────────────────────

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2 py-2">
      <span className="text-xs text-muted-foreground w-28 shrink-0 pt-0.5">
        {label}
      </span>
      <span className="text-sm text-foreground flex-1">{value}</span>
    </div>
  )
}

// ─── Emergency contacts ───────────────────────────────────────────────────────

interface EmergencyContactsProps {
  contacts: EmergencyContact[]
}

function EmergencyContacts({ contacts }: EmergencyContactsProps) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground transition-colors"
      >
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        Emergency Contacts ({contacts.length})
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          {contacts.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">No emergency contacts recorded</p>
          ) : (
            contacts.map((contact, i) => (
              <div
                key={i}
                className="rounded-md bg-muted px-3 py-2 text-sm"
              >
                <span className="font-medium text-foreground">{contact.name}</span>
                <span className="text-muted-foreground"> · {contact.relationship}</span>
                <span className="text-muted-foreground"> · {contact.phone}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ─── Demographics card ───────────────────────────────────────────────────────

interface DemographicsCardProps {
  patient: Patient
  edits: Partial<EditablePatientFields>
  onSave: (key: keyof EditablePatientFields, value: string) => void
}

function DemographicsCard({ patient, edits, onSave }: DemographicsCardProps) {
  const age = calculateAge(patient.dob)
  const fullName = `${patient.name.first} ${patient.name.last}`
  const sex = patient.sex.charAt(0).toUpperCase() + patient.sex.slice(1)

  const phone = edits.phone ?? patient.phone ?? ""
  const email = edits.email ?? patient.email ?? ""
  const address = edits.address ?? patient.address ?? ""

  return (
    <div className="bg-bg-surface border border-border rounded-lg p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">
        Demographics
      </h2>

      <div className="divide-y divide-border">
        <ReadOnlyField label="Full Name" value={fullName} />
        <ReadOnlyField label="Date of Birth" value={formatDob(patient.dob)} />
        <ReadOnlyField label="Age" value={`${age} years`} />
        <ReadOnlyField label="Sex" value={sex} />
        <ReadOnlyField label="Health Number" value={patient.healthNumber || "Not assigned"} />
        <EditableField label="Address" value={address} fieldKey="address" onSave={onSave} />
        <EditableField label="Phone" value={phone} fieldKey="phone" onSave={onSave} />
        <EditableField label="Email" value={email} fieldKey="email" onSave={onSave} />
      </div>

      <Separator className="mt-4" />
      <EmergencyContacts contacts={patient.emergencyContacts} />
    </div>
  )
}

// ─── Allergy badge ────────────────────────────────────────────────────────────

function AllergyBadge({ allergy }: { allergy: Allergy }) {
  const severityClass = {
    severe: "bg-[color-mix(in_oklch,var(--danger)_10%,transparent)] text-[var(--danger)] border border-[color-mix(in_oklch,var(--danger)_20%,transparent)]",
    moderate: "bg-[color-mix(in_oklch,var(--warning)_10%,transparent)] text-[var(--warning)] border border-[color-mix(in_oklch,var(--warning)_20%,transparent)]",
    mild: "bg-muted text-muted-foreground border border-border",
  }[allergy.severity]

  const label = allergy.reaction
    ? `${allergy.name} — ${allergy.reaction}`
    : allergy.name

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        severityClass,
      )}
    >
      {label}
    </span>
  )
}

// ─── Medication row ───────────────────────────────────────────────────────────

function MedicationRow({ medication }: { medication: Medication }) {
  return (
    <div className="flex items-start gap-3 rounded-md bg-muted px-3 py-2.5">
      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[var(--success)]" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground leading-snug">
          {medication.name}
          {medication.dose && (
            <span className="font-normal text-muted-foreground"> · {medication.dose}</span>
          )}
        </p>
        <p className="text-sm text-muted-foreground">{medication.instructions}</p>
        {medication.prescribedDate && (
          <p className="font-mono text-xs text-muted-foreground mt-0.5">
            Rx {medication.prescribedDate}
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Problem row ──────────────────────────────────────────────────────────────

function ProblemRow({ problem }: { problem: Problem }) {
  const isActive = problem.status === "active"

  return (
    <div className="flex items-center gap-3 py-2">
      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          isActive ? "bg-[var(--success)]" : "bg-muted-foreground",
        )}
      />
      <span className="font-mono text-xs text-[var(--primary)] bg-[color-mix(in_oklch,var(--primary)_8%,transparent)] px-1.5 py-0.5 rounded shrink-0">
        {problem.code}
      </span>
      <span className="text-sm text-foreground flex-1">{problem.description}</span>
    </div>
  )
}

// ─── Clinical context card ────────────────────────────────────────────────────

function ClinicalContextCard({ patient }: { patient: Patient }) {
  return (
    <div className="bg-bg-surface border border-border rounded-lg p-5 space-y-6">

      {/* Allergies */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Allergies
        </h2>
        {patient.allergies.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No known allergies</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {patient.allergies.map((allergy, i) => (
              <AllergyBadge key={i} allergy={allergy} />
            ))}
          </div>
        )}
      </section>

      <Separator />

      {/* Medications */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Medications
        </h2>
        {patient.medications.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No active medications</p>
        ) : (
          <div className="space-y-2">
            {patient.medications.map((med, i) => (
              <MedicationRow key={i} medication={med} />
            ))}
          </div>
        )}
      </section>

      <Separator />

      {/* Problems */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Problems
        </h2>
        {patient.problems.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No recorded problems</p>
        ) : (
          <div className="divide-y divide-border">
            {patient.problems.map((problem, i) => (
              <ProblemRow key={i} problem={problem} />
            ))}
          </div>
        )}
      </section>

      <Separator />

      {/* Immunization status */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Immunization Status
        </h2>
        {patient.immunizationUpToDate ? (
          <div className="flex items-center gap-2 text-sm text-[var(--success)]">
            <CheckCircle size={16} />
            <span>Immunizations up to date</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-[var(--warning)]">
            <AlertTriangle size={16} />
            <span>Immunization review needed</span>
          </div>
        )}
      </section>
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const { id } = useParams<{ id: string }>()
  // Resolve to the mock EMR patient or a placeholder for a backend id (never 404).
  const patient = resolvePatient(id)

  const [edits, setEdits] = useState<Partial<EditablePatientFields>>({})

  function handleSave(key: keyof EditablePatientFields, value: string) {
    setEdits((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      className="grid grid-cols-1 md:grid-cols-2 gap-6"
    >
      <DemographicsCard patient={patient} edits={edits} onSave={handleSave} />
      <ClinicalContextCard patient={patient} />
    </motion.div>
  )
}
