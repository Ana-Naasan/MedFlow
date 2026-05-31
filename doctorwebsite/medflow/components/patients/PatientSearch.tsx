"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { User } from "lucide-react"
import {
  CommandDialog,
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command"
import { useMedFlowStore } from "@/lib/store"
import { patients } from "@/lib/mock-data/patients"
import type { Patient } from "@/lib/types"

function filterPatients(query: string): Patient[] {
  if (!query.trim()) return []
  const q = query.toLowerCase()
  return patients.filter(
    (p) =>
      p.name.first.toLowerCase().includes(q) ||
      p.name.last.toLowerCase().includes(q) ||
      p.id.includes(q) ||
      p.healthNumber.toLowerCase().includes(q)
  )
}

function getRecentPatients(ids: string[]): Patient[] {
  return ids
    .map((id) => patients.find((p) => p.id === id))
    .filter((p): p is Patient => p !== undefined)
}

export function PatientSearch() {
  const router = useRouter()
  const searchOpen = useMedFlowStore((s) => s.searchOpen)
  const setSearchOpen = useMedFlowStore((s) => s.setSearchOpen)
  const addRecentPatient = useMedFlowStore((s) => s.addRecentPatient)
  const recentPatientIds = useMedFlowStore((s) => s.recentPatientIds)

  const [query, setQuery] = useState("")

  // ⌘K / Ctrl+K toggle
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setSearchOpen(!searchOpen)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [searchOpen, setSearchOpen])

  // Reset the query in the same handler that toggles the dialog (no
  // effect-driven setState): clear it whenever the dialog transitions closed.
  function handleOpenChange(next: boolean) {
    setSearchOpen(next)
    if (!next) setQuery("")
  }

  function handleSelect(patientId: string) {
    addRecentPatient(patientId)
    handleOpenChange(false)
    router.push(`/patients/${patientId}/profile`)
  }

  const filteredPatients = filterPatients(query)
  const recentPatients = getRecentPatients(recentPatientIds)
  const showRecents = !query.trim() && recentPatients.length > 0
  const showResults = query.trim().length > 0

  return (
    <CommandDialog
      open={searchOpen}
      onOpenChange={handleOpenChange}
      title="Search patients"
      description="Search by name, patient ID, or health card number"
    >
      <Command shouldFilter={false}>
        <CommandInput
          placeholder="Search patients..."
          value={query}
          onValueChange={setQuery}
          aria-label="Search patients by name, ID, or health card"
        />
        <CommandList>
          {showRecents && (
            <CommandGroup heading="Recent Patients">
              {recentPatients.map((patient) => (
                <PatientCommandItem
                  key={patient.id}
                  patient={patient}
                  onSelect={handleSelect}
                />
              ))}
            </CommandGroup>
          )}

          {showResults && filteredPatients.length > 0 && (
            <CommandGroup heading="Results">
              {filteredPatients.map((patient) => (
                <PatientCommandItem
                  key={patient.id}
                  patient={patient}
                  onSelect={handleSelect}
                />
              ))}
            </CommandGroup>
          )}

          {showResults && filteredPatients.length === 0 && (
            <CommandEmpty>No patients found for &ldquo;{query}&rdquo;</CommandEmpty>
          )}

          {!showRecents && !showResults && (
            <CommandEmpty>Start typing to search patients</CommandEmpty>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  )
}

interface PatientCommandItemProps {
  patient: Patient
  onSelect: (id: string) => void
}

function PatientCommandItem({ patient, onSelect }: PatientCommandItemProps) {
  const fullName = `${patient.name.first} ${patient.name.last}`
  const primaryCondition = patient.problems.find((p) => p.status === "active")?.description

  return (
    <CommandItem
      value={`${patient.id}-${fullName}`}
      onSelect={() => onSelect(patient.id)}
      aria-label={`Open chart for ${fullName}, ID ${patient.id}`}
    >
      <div className="flex items-center gap-3 w-full min-w-0">
        <div
          className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted"
          aria-hidden="true"
        >
          <User className="size-3.5 text-muted-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">
            {fullName}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            ID {patient.id}
            {patient.location ? ` · ${patient.location}` : ""}
            {primaryCondition ? ` · ${primaryCondition}` : ""}
          </p>
        </div>
      </div>
    </CommandItem>
  )
}
