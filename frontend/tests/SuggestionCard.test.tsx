// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SuggestionCard } from "../components/SuggestionCard";
import type { Hypothesis } from "../lib/types";

vi.mock("../components/CitationChip", () => ({
  CitationChip: ({
    citation,
  }: {
    citation: { label: string | null; ref: string };
  }) => <span data-testid="citation-chip">{citation.label ?? citation.ref}</span>,
}));

const mockHypothesis: Hypothesis = {
  id: "hyp-001",
  title: "Possible medication-related bleeding risk",
  why: "The patient is on aspirin and the evidence store includes a cited DDInter interaction.",
  severity: "moderate",
  confidence: "low",
  citations: [
    { kind: "resource", ref: "Patient/pat-001", label: "Patient/pat-001" },
    { kind: "evidence", ref: "ddinter-aspirin-warfarin", label: "DDInter aspirin-warfarin" },
  ],
};

describe("SuggestionCard", () => {
  it("renders the why-line", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(
      screen.getByText(
        "The patient is on aspirin and the evidence store includes a cited DDInter interaction."
      )
    ).toBeInTheDocument();
  });

  it("renders the severity badge", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(screen.getByText(/moderate/)).toBeInTheDocument();
  });

  it("renders the confidence badge", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(screen.getByText(/low confidence/)).toBeInTheDocument();
  });

  it("renders a CitationChip for each citation", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(screen.getAllByTestId("citation-chip")).toHaveLength(2);
  });

  it("renders the hypothesis title", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(screen.getByText("Possible medication-related bleeding risk")).toBeInTheDocument();
  });

  it("does not render action buttons when no callbacks are provided", () => {
    render(<SuggestionCard hypothesis={mockHypothesis} patientId="pat-001" />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dismiss/i })).not.toBeInTheDocument();
  });

  it("renders Approve and Dismiss buttons when callbacks are provided", () => {
    render(
      <SuggestionCard
        hypothesis={mockHypothesis}
        patientId="pat-001"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dismiss/i })).toBeInTheDocument();
  });

  it("shows resolved status and hides buttons when status is set", () => {
    render(
      <SuggestionCard
        hypothesis={mockHypothesis}
        patientId="pat-001"
        onConfirm={vi.fn()}
        onDismiss={vi.fn()}
        status="confirmed"
      />
    );
    expect(screen.getByText(/✓ Approved/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });
});
