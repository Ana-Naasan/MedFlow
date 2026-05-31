// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

import { PatientTabs } from "../components/layout/PatientTabs";

describe("PatientTabs", () => {
  it("renders all 7 patient tabs", () => {
    vi.mocked(usePathname).mockReturnValue("/patients/pat-001/profile");
    render(<PatientTabs patientId="pat-001" />);
    for (const slug of [
      "profile",
      "packet",
      "records",
      "edocuments",
      "investigations",
      "notes",
      "billing",
    ]) {
      expect(screen.getByTestId(`tab-${slug}`)).toBeInTheDocument();
    }
  });

  it("each tab links to /patients/{id}/{slug}", () => {
    vi.mocked(usePathname).mockReturnValue("/patients/pat-001/profile");
    render(<PatientTabs patientId="pat-001" />);
    expect(screen.getByTestId("tab-packet")).toHaveAttribute(
      "href",
      "/patients/pat-001/packet",
    );
    expect(screen.getByTestId("tab-billing")).toHaveAttribute(
      "href",
      "/patients/pat-001/billing",
    );
  });

  it("marks the active tab with aria-current=page", () => {
    vi.mocked(usePathname).mockReturnValue("/patients/pat-001/packet");
    render(<PatientTabs patientId="pat-001" />);
    expect(screen.getByTestId("tab-packet")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByTestId("tab-profile")).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("treats a child route as active too", () => {
    vi.mocked(usePathname).mockReturnValue("/patients/pat-001/records/x");
    render(<PatientTabs patientId="pat-001" />);
    expect(screen.getByTestId("tab-records")).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
