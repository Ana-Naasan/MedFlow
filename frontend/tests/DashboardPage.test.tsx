// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/usePatients", () => ({
  usePatients: vi.fn(),
}));

import DashboardPage from "../app/(dashboard)/dashboard/page";
import { usePatients } from "../lib/usePatients";

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading skeletons while patients fetch", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as never);
    render(<DashboardPage />);
    expect(screen.getByText(/clinical dashboard/i)).toBeInTheDocument();
    // Stat tile reads "…" while loading:
    expect(screen.getByTestId("stat-patients")).toHaveTextContent("…");
    expect(screen.getByLabelText(/loading patients/i)).toBeInTheDocument();
  });

  it("shows the patient count and a list when data resolves", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [{ id: "pat-001" }, { id: "DEMO-001" }, { id: "PARTIAL-001" }],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DashboardPage />);
    expect(screen.getByTestId("stat-patients")).toHaveTextContent("3");
    const list = screen.getByTestId("patients-list");
    expect(within(list).getByText("pat-001")).toBeInTheDocument();
    expect(within(list).getByText("DEMO-001")).toBeInTheDocument();
  });

  it("links each row to the profile tab", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [{ id: "DEMO-001" }],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DashboardPage />);
    const link = screen.getByRole("link", { name: /DEMO-001/i });
    expect(link).toHaveAttribute("href", "/patients/DEMO-001/profile");
  });

  it("shows the empty-state hint when the cache is empty", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DashboardPage />);
    expect(screen.getByTestId("patients-empty")).toBeInTheDocument();
  });

  it("shows the error path with the underlying error message", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("HTTP 401"),
    } as never);
    render(<DashboardPage />);
    expect(screen.getByTestId("patients-error")).toHaveTextContent(/HTTP 401/);
  });

  it("the See all link points at /directory", () => {
    vi.mocked(usePatients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<DashboardPage />);
    expect(screen.getByTestId("see-all-patients")).toHaveAttribute(
      "href",
      "/directory",
    );
  });
});
