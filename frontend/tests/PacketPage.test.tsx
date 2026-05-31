// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/api", () => ({
  $api: { useQuery: vi.fn() },
}));

vi.mock("../components/SuggestionCard", () => ({
  SuggestionCard: ({ hypothesis }: { hypothesis: { title: string } }) => (
    <div data-testid="suggestion-card">{hypothesis.title}</div>
  ),
}));

vi.mock("../components/CompletenessIndicator", () => ({
  CompletenessIndicator: () => <div data-testid="completeness-indicator" />,
}));

import { $api } from "../lib/api";
import Page from "../app/(provider)/packet/page";

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
    vi.mocked($api.useQuery).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);
    render(<Page />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("shows error state when fetch fails", () => {
    vi.mocked($api.useQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as never);
    render(<Page />);
    expect(screen.getByText(/failed/i)).toBeInTheDocument();
  });

  it("shows error when data is undefined after fetch", () => {
    vi.mocked($api.useQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as never);
    render(<Page />);
    expect(screen.getByText(/failed/i)).toBeInTheDocument();
  });

  it("renders a SuggestionCard for each hypothesis", () => {
    vi.mocked($api.useQuery).mockReturnValue({
      data: mockPacket,
      isLoading: false,
      isError: false,
    } as never);
    render(<Page />);
    expect(screen.getAllByTestId("suggestion-card")).toHaveLength(1);
    expect(
      screen.getByText("Possible medication-related bleeding risk")
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
    vi.mocked($api.useQuery).mockReturnValue({
      data: packetWithCompleteness,
      isLoading: false,
      isError: false,
    } as never);
    render(<Page />);
    expect(screen.getByTestId("completeness-indicator")).toBeInTheDocument();
  });

  it("does not render CompletenessIndicator when completeness is empty", () => {
    const packetNoCompleteness = { ...mockPacket, completeness: [] };
    vi.mocked($api.useQuery).mockReturnValue({
      data: packetNoCompleteness,
      isLoading: false,
      isError: false,
    } as never);
    render(<Page />);
    expect(screen.queryByTestId("completeness-indicator")).not.toBeInTheDocument();
  });
});
