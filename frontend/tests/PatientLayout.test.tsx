// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import PatientLayout from "../app/(dashboard)/patients/[id]/layout";
import { usePathname } from "next/navigation";

describe("PatientLayout", () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue("/patients/pat-001/profile");
  });

  it("renders the patient header + tabs + child content", () => {
    render(
      <PatientLayout params={{ id: "DEMO-001" }}>
        <div data-testid="child">Profile content</div>
      </PatientLayout>,
    );
    expect(screen.getByTestId("patient-header-id")).toHaveTextContent("DEMO-001");
    expect(screen.getByTestId("patient-tabs")).toBeInTheDocument();
    expect(screen.getByTestId("child")).toHaveTextContent("Profile content");
  });

  it("decodes URL-encoded patient ids", () => {
    render(
      <PatientLayout params={{ id: "pat%2D001" }}>
        <div data-testid="child" />
      </PatientLayout>,
    );
    expect(screen.getByTestId("patient-header-id")).toHaveTextContent("pat-001");
  });
});
