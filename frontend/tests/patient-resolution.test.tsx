import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PatientHeader } from "@/components/layout/PatientHeader";
import { getPatientById, resolvePatient } from "@/lib/mock-data/patients";

describe("resolvePatient", () => {
  it("returns the mock EMR patient for a known mock id", () => {
    const patient = resolvePatient("24884");
    expect(patient.id).toBe("24884");
    expect(patient.name.last).toBe("Whitmore");
  });

  it("returns a complete placeholder for a real backend id the mock EMR lacks", () => {
    // pat-001 is a backend seed, NOT in the mock list — this is exactly the id that
    // used to 404 the whole /patients/[id] subtree (incl. the packet page).
    expect(getPatientById("pat-001")).toBeUndefined();

    const patient = resolvePatient("pat-001");
    expect(patient.id).toBe("pat-001");
    // Every required Patient field must be present so the header/pages don't crash.
    expect(patient.name.first).toBeTruthy();
    expect(patient.name.last).toBeTruthy();
    expect(Array.isArray(patient.medications)).toBe(true);
    expect(Array.isArray(patient.problems)).toBe(true);
  });
});

describe("PatientHeader for a backend-only patient", () => {
  it("renders the backend id and never shows NaN / Invalid Date for unknown demographics", () => {
    render(<PatientHeader patient={resolvePatient("pat-001")} />);

    // The backend id is shown (PHN + ID block, rendered more than once across breakpoints).
    expect(screen.getAllByText(/pat-001/).length).toBeGreaterThan(0);
    // Unknown demographics must never render as NaN / Invalid Date.
    expect(screen.queryByText(/NaN|Invalid Date/)).toBeNull();
  });
});
