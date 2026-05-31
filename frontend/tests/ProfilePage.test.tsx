// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("../lib/usePatientResource", () => ({
  usePatientResource: vi.fn(),
}));

import ProfilePage from "../app/(dashboard)/patients/[id]/profile/page";
import { useParams } from "next/navigation";

import { usePatientResource } from "../lib/usePatientResource";

const PATIENT = {
  resourceType: "Patient",
  id: "DEMO-001",
  identifier: [{ system: "urn:mrn", value: "MRN-DEMO-001" }],
  gender: "female",
  birthDate: "1942-03-15",
};

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useParams).mockReturnValue({ id: "DEMO-001" });
  });

  it("calls usePatientResource with the URL patient id", () => {
    vi.mocked(usePatientResource).mockReturnValue({
      data: PATIENT,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<ProfilePage />);
    expect(usePatientResource).toHaveBeenCalledWith(
      "DEMO-001",
      "Patient",
      "DEMO-001",
    );
  });

  it("decodes a URL-encoded patient id from the route param", () => {
    vi.mocked(useParams).mockReturnValue({ id: "pat%2D001" });
    vi.mocked(usePatientResource).mockReturnValue({
      data: { resourceType: "Patient", id: "pat-001" },
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<ProfilePage />);
    expect(usePatientResource).toHaveBeenCalledWith(
      "pat-001",
      "Patient",
      "pat-001",
    );
  });

  it("renders the demographic fields when the resource resolves", () => {
    vi.mocked(usePatientResource).mockReturnValue({
      data: PATIENT,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<ProfilePage />);
    const fields = screen.getByTestId("profile-fields");
    expect(fields).toHaveTextContent("DEMO-001");
    expect(fields).toHaveTextContent(/Patient/); // resourceType
    expect(fields).toHaveTextContent("MRN-DEMO-001");
    expect(fields).toHaveTextContent("female");
    expect(fields).toHaveTextContent("1942-03-15");
  });

  it("shows a skeleton while loading", () => {
    vi.mocked(usePatientResource).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as never);
    render(<ProfilePage />);
    expect(screen.getByLabelText(/loading profile/i)).toBeInTheDocument();
  });

  it("surfaces the failure cause on error", () => {
    vi.mocked(usePatientResource).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("HTTP 404"),
    } as never);
    render(<ProfilePage />);
    expect(screen.getByTestId("profile-error")).toHaveTextContent(/HTTP 404/);
  });
});
