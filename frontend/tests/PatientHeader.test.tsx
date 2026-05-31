// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PatientHeader } from "../components/layout/PatientHeader";

describe("PatientHeader", () => {
  it("renders the patient id", () => {
    render(<PatientHeader patientId="DEMO-001" />);
    expect(screen.getByTestId("patient-header-id")).toHaveTextContent("DEMO-001");
  });

  it("uses an h1 for the patient id (top-of-page identity)", () => {
    render(<PatientHeader patientId="X" />);
    expect(screen.getByRole("heading", { level: 1, name: "X" })).toBeInTheDocument();
  });
});
