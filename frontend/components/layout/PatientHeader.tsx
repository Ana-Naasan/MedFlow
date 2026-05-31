import { User } from "lucide-react";

interface PatientHeaderProps {
  patientId: string;
}

/**
 * Slim patient identity strip above the tabs. The full medflow PatientHeader
 * displays demographics (DOB, sex, MRN) — we don't have a single API surface
 * that returns that synthesised yet, so this phase ships the id-only header.
 * The patient profile tab fetches and displays demographics.
 */
export function PatientHeader({ patientId }: PatientHeaderProps) {
  return (
    <div className="flex items-center gap-3 px-6 py-4 bg-mf-paper">
      <div
        className="flex size-10 items-center justify-center rounded-full border-2 border-mf-ink bg-mf-clinician text-mf-ink"
        aria-hidden
      >
        <User className="size-5" />
      </div>
      <div className="min-w-0">
        <p className="mf-eyebrow !text-[10px]">Patient</p>
        <h1
          className="mf-display text-xl font-semibold leading-tight text-foreground"
          data-testid="patient-header-id"
        >
          {patientId}
        </h1>
      </div>
    </div>
  );
}
