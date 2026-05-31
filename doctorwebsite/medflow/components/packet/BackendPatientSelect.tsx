"use client"

import { Database } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface BackendPatientSelectProps {
  /** Backend patient ids from `usePatients()`. */
  patientIds: string[]
  /** The currently active backend patient id driving the packet query. */
  value: string
  /** Fired with the chosen backend id (never null). */
  onChange: (id: string) => void
  /** Whether the route's mock id was matched in the backend list. */
  matchedRoute: boolean
}

/**
 * Reconciles MedFlow's mock patient ids with the real backend. MedFlow's route
 * ids will not exist in the backend, so the operator picks which backend
 * patient to review; the selected id is what drives `usePacket(...)`.
 */
export function BackendPatientSelect({
  patientIds,
  value,
  onChange,
  matchedRoute,
}: BackendPatientSelectProps) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <Database
        size={16}
        className="shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
      <label
        htmlFor="backend-patient-select"
        className="text-sm font-medium text-foreground"
      >
        Backend patient
      </label>
      <Select
        value={value}
        // @base-ui passes string | null — coerce so we never clear the driver.
        onValueChange={(v) => onChange(v ?? value)}
      >
        <SelectTrigger id="backend-patient-select" className="min-w-56">
          <SelectValue placeholder="Select a backend patient" />
        </SelectTrigger>
        <SelectContent>
          {patientIds.map((id) => (
            <SelectItem key={id} value={id}>
              {id}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {!matchedRoute && (
        <span className="text-xs text-muted-foreground">
          This chart&apos;s id is not in the backend — showing a backend patient.
        </span>
      )}
    </div>
  )
}
