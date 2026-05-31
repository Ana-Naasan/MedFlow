// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/usePacket", async () => {
  const actual = await vi.importActual<typeof import("../lib/usePacket")>(
    "../lib/usePacket",
  );
  return {
    ...actual,
    usePacket: vi.fn(),
  };
});

vi.mock("../components/SuggestionCard", () => ({
  SuggestionCard: ({ hypothesis }: { hypothesis: { title: string } }) => (
    <div data-testid="suggestion-card">{hypothesis.title}</div>
  ),
}));

vi.mock("../components/CompletenessIndicator", () => ({
  CompletenessIndicator: () => <div data-testid="completeness-indicator" />,
}));

import Page from "../app/(provider)/packet/page";
import { PacketLoadError, usePacket } from "../lib/usePacket";

const mockPacket = {
  patient_id: "pat-001",
  summary_markdown: "### Cited suggestions",
  hypotheses: [
    {
      id: "hyp-001",
      title: "Possible medication-related bleeding risk",
      why: "The patient is on aspirin.",
      severity: "moderate",
      confidence: "low",
      citations: [],
    },
  ],
  data_gaps: ["Renal function labs missing"],
  cache_status: "HIT",
};

describe("ProviderPacketPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading state while packet is fetching", () => {
    vi.mocked(usePacket).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as never);
    render(<Page />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows the diagnostic failure panel with status when the fetch errors", () => {
    const diagError = new PacketLoadError({
      status: 401,
      body: { detail: "Missing bearer token" },
      url: "http://localhost:8000/patients/pat-001/packet",
      elapsedMs: 42,
    });
    vi.mocked(usePacket).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: diagError,
    } as never);
    render(<Page />);
    expect(screen.getByTestId("packet-load-failure")).toBeInTheDocument();
    expect(screen.getByTestId("packet-failure-status")).toHaveTextContent("401");
    expect(screen.getByTestId("packet-failure-url")).toHaveTextContent(
      "http://localhost:8000/patients/pat-001/packet",
    );
    expect(screen.getByTestId("packet-failure-elapsed")).toHaveTextContent("42 ms");
    expect(screen.getByTestId("packet-failure-body")).toHaveTextContent(
      /Missing bearer token/,
    );
  });

  it("falls back to the failure panel when data is undefined without an error", () => {
    vi.mocked(usePacket).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<Page />);
    expect(screen.getByTestId("packet-load-failure")).toBeInTheDocument();
    // No real diagnostic info — status falls back to "no response":
    expect(screen.getByTestId("packet-failure-status")).toHaveTextContent(
      /no response/i,
    );
  });

  it("renders a SuggestionCard for each hypothesis", () => {
    vi.mocked(usePacket).mockReturnValue({
      data: mockPacket,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<Page />);
    expect(screen.getAllByTestId("suggestion-card")).toHaveLength(1);
    expect(
      screen.getByText("Possible medication-related bleeding risk"),
    ).toBeInTheDocument();
  });

  it("renders CompletenessIndicator when packet has completeness data", () => {
    const packetWithCompleteness = {
      ...mockPacket,
      completeness: [
        { category: "Medications", documented: true, gap_note: null },
        { category: "Labs", documented: false, gap_note: "Order BMP" },
      ],
    };
    vi.mocked(usePacket).mockReturnValue({
      data: packetWithCompleteness,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<Page />);
    expect(screen.getByTestId("completeness-indicator")).toBeInTheDocument();
  });

  it("does not render CompletenessIndicator when completeness is empty", () => {
    const packetNoCompleteness = { ...mockPacket, completeness: [] };
    vi.mocked(usePacket).mockReturnValue({
      data: packetNoCompleteness,
      isLoading: false,
      isError: false,
      error: null,
    } as never);
    render(<Page />);
    expect(screen.queryByTestId("completeness-indicator")).not.toBeInTheDocument();
  });
});
