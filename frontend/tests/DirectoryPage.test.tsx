// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/usePatients", () => ({
  usePatients: vi.fn(),
}));

import DirectoryPage from "../app/(dashboard)/directory/page";
import { usePatients } from "../lib/usePatients";

describe("DirectoryPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows a loading skeleton while patients fetch", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as never);
    render(<DirectoryPage />);
    expect(screen.getByLabelText(/loading directory/i)).toBeInTheDocument();
  });

  it("renders one row per patient with a link to the profile tab", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [{ id: "pat-001" }, { id: "DEMO-001" }],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DirectoryPage />);
    expect(screen.getByTestId("directory-table")).toBeInTheDocument();
    expect(screen.getByTestId("directory-row-pat-001")).toHaveAttribute(
      "href",
      "/patients/pat-001/profile",
    );
    expect(screen.getByTestId("directory-row-DEMO-001")).toHaveAttribute(
      "href",
      "/patients/DEMO-001/profile",
    );
  });

  it("shows the empty state when no patients", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DirectoryPage />);
    expect(screen.getByTestId("directory-empty")).toBeInTheDocument();
  });

  it("surfaces the failure with the underlying error message", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Packet fetch failed: HTTP 401"),
    } as never);
    render(<DirectoryPage />);
    expect(screen.getByTestId("directory-error")).toHaveTextContent(/HTTP 401/);
  });
});
